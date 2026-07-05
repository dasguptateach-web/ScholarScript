import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import requests

from .config import Config


def deploy_to_github_pages(config: Config, token: Optional[str] = None, repo: Optional[str] = None):
    """Deploy the built site to GitHub Pages using the GitHub API."""
    public_dir = config.get_public_dir()
    if not public_dir.exists() or not any(public_dir.iterdir()):
        print("No built site found. Run build first.")
        return False

    # Resolve token (env var > param > saved file > prompt)
    if not token:
        token = os.environ.get("GITHUB_TOKEN") or _load_token(config)
    if not token:
        print("GitHub token required. Set GITHUB_TOKEN env var or create token at:")
        print("  https://github.com/settings/tokens (scope: repo, pages)")
        try:
            token_input = input("Paste your GitHub token: ").strip()
            if token_input:
                token = token_input
                _save_token(config, token)
        except (EOFError, OSError):
            print("No interactive input available. Set GITHUB_TOKEN env var and re-run.")
            return False
    if not token:
        return False

    # Resolve repo
    if not repo:
        repo = os.environ.get("GITHUB_REPO")
    if not repo:
        try:
            repo_input = input("GitHub repo (e.g. 'username/repo'): ").strip()
            if repo_input:
                repo = repo_input
        except (EOFError, OSError):
            print("No interactive input. Set GITHUB_REPO env var and re-run.")
            return False
    if not repo:
        return False

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # If repo has no username prefix, get the authenticated user
    if "/" not in repo:
        r = requests.get("https://api.github.com/user", headers=headers)
        if r.status_code == 200:
            username = r.json()["login"]
            repo = f"{username}/{repo}"
            print(f"Using repo: {repo}")
        else:
            print("Could not determine GitHub username. Use format 'username/repo'.")
            return False

    # Check if repo exists; if not, create it
    r = requests.get(f"https://api.github.com/repos/{repo}", headers=headers)
    if r.status_code == 404:
        username = repo.split("/")[0]
        r2 = requests.post(
            "https://api.github.com/user/repos",
            headers=headers,
            json={"name": repo.split("/")[1], "auto_init": True},
        )
        if r2.status_code not in (201, 422):
            print(f"Failed to create repo: {r2.status_code} {r2.text[:200]}")
            return False
        print(f"Created repository {repo}")

    # Get the default branch
    r = requests.get(f"https://api.github.com/repos/{repo}", headers=headers)
    if r.status_code != 200:
        print(f"Failed to access repo: {r.status_code}")
        return False
    default_branch = r.json().get("default_branch", "main")

    # Create or update gh-pages branch by uploading all files via API
    # We'll use the contents API to create/update files
    _upload_directory(public_dir, "", repo, default_branch, headers, token)

    # Enable GitHub Pages
    pages_config = {
        "source": {"branch": default_branch, "path": "/"},
    }
    r = requests.post(
        f"https://api.github.com/repos/{repo}/pages",
        headers=headers,
        json=pages_config,
    )
    if r.status_code == 201:
        print(f"GitHub Pages enabled at https://{repo.split('/')[0]}.github.io/{repo.split('/')[1]}/")
    elif r.status_code == 409:
        print(f"Pages already configured. Site at https://{repo.split('/')[0]}.github.io/{repo.split('/')[1]}/")
    else:
        # Try PUT if already exists
        r = requests.put(
            f"https://api.github.com/repos/{repo}/pages",
            headers=headers,
            json=pages_config,
        )
        if r.status_code in (200, 204, 201):
            print(f"Pages updated. Site at https://{repo.split('/')[0]}.github.io/{repo.split('/')[1]}/")
        else:
            print(f"Pages config: {r.status_code} - set manually in repo Settings > Pages")

    return True


def _upload_directory(local_dir: Path, prefix: str, repo: str, branch: str, headers: dict, token: str):
    """Recursively upload all files in a directory to GitHub using the Contents API."""
    # Get the current commit SHA of the branch to use as parent
    sha_url = f"https://api.github.com/repos/{repo}/git/refs/heads/{branch}"
    r = requests.get(sha_url, headers=headers)
    if r.status_code != 200:
        print(f"Cannot access branch '{branch}'. Make sure the repo has at least one commit.")
        return

    # Build a tree from all files
    tree = []
    for file_path in sorted(local_dir.rglob("*")):
        if file_path.is_dir():
            continue
        rel = file_path.relative_to(local_dir).as_posix()
        content = file_path.read_bytes()
        encoded = base64.b64encode(content).decode()

        tree.append({
            "path": rel,
            "mode": "100644",
            "type": "blob",
            "content": base64.b64decode(encoded).decode("utf-8", errors="replace"),
        })

    # Create a tree
    r = requests.post(
        f"https://api.github.com/repos/{repo}/git/trees",
        headers=headers,
        json={"tree": [{"path": t["path"], "mode": t["mode"], "type": t["type"], "content": t["content"]} for t in tree]},
    )
    if r.status_code != 201:
        print(f"Failed to create tree: {r.status_code} {r.text[:300]}")
        return

    tree_sha = r.json()["sha"]

    # Get the latest commit on the branch
    r = requests.get(f"https://api.github.com/repos/{repo}/git/ref/heads/{branch}", headers=headers)
    if r.status_code != 200:
        print(f"Cannot get branch ref: {r.status_code}")
        return
    parent_sha = r.json()["object"]["sha"]

    # Create a commit
    r = requests.post(
        f"https://api.github.com/repos/{repo}/git/commits",
        headers=headers,
        json={
            "message": "ScholarScript auto-deploy",
            "tree": tree_sha,
            "parents": [parent_sha],
        },
    )
    if r.status_code != 201:
        print(f"Failed to create commit: {r.status_code} {r.text[:300]}")
        return
    commit_sha = r.json()["sha"]

    # Update the branch reference
    r = requests.patch(
        f"https://api.github.com/repos/{repo}/git/refs/heads/{branch}",
        headers=headers,
        json={"sha": commit_sha, "force": True},
    )
    if r.status_code in (200, 201):
        print(f"Deployed {len(tree)} files to {repo}/{branch}")
    else:
        print(f"Failed to update branch: {r.status_code} {r.text[:200]}")


def _load_token(config: Config) -> Optional[str]:
    token_file = config.root / ".github_token"
    if token_file.exists():
        return token_file.read_text().strip()
    return None


def _save_token(config: Config, token: str):
    token_file = config.root / ".github_token"
    token_file.write_text(token)
    print(f"Token saved to {token_file} (add to .gitignore!)")
