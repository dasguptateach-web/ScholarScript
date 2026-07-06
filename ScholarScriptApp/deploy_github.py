import base64
import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Optional, Tuple


GITHUB_API = "https://api.github.com"


def _api_request(url: str, method: str, body: dict = None, token: str = "", accept: str = "application/vnd.github+json") -> Tuple[int, dict]:
    headers = {
        "Accept": accept,
        "User-Agent": "ScholarScript-Portable/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:500]
        except Exception:
            pass
        return e.code, {"message": str(e), "detail": detail}
    except Exception as e:
        return 0, {"message": str(e)}


def get_default_branch(repo: str, token: str) -> Optional[str]:
    status, data = _api_request(f"{GITHUB_API}/repos/{repo}", "GET", token=token)
    if status == 200:
        return data.get("default_branch", "main")
    return "main"


def create_blob(repo: str, content: str, token: str) -> Optional[str]:
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    status, data = _api_request(
        f"{GITHUB_API}/repos/{repo}/git/blobs",
        "POST",
        {"content": encoded, "encoding": "base64"},
        token,
    )
    if status == 201:
        return data.get("sha")
    return None


def get_ref_sha(repo: str, branch: str, token: str) -> Optional[str]:
    status, data = _api_request(f"{GITHUB_API}/repos/{repo}/git/ref/heads/{branch}", "GET", token=token)
    if status == 200:
        return data.get("object", {}).get("sha")
    return None


def get_commit_tree(repo: str, commit_sha: str, token: str) -> Optional[str]:
    status, data = _api_request(f"{GITHUB_API}/repos/{repo}/git/commits/{commit_sha}", "GET", token=token)
    if status == 200:
        return data.get("tree", {}).get("sha")
    return None


def create_tree(repo: str, base_tree: str, blobs: List[dict], token: str) -> Optional[str]:
    status, data = _api_request(
        f"{GITHUB_API}/repos/{repo}/git/trees",
        "POST",
        {"base_tree": base_tree, "tree": blobs},
        token,
    )
    if status == 201:
        return data.get("sha")
    return None


def create_commit(repo: str, tree_sha: str, parent_sha: str, message: str, token: str) -> Optional[str]:
    status, data = _api_request(
        f"{GITHUB_API}/repos/{repo}/git/commits",
        "POST",
        {"message": message, "tree": tree_sha, "parents": [parent_sha]},
        token,
    )
    if status == 201:
        return data.get("sha")
    return None


def update_ref(repo: str, branch: str, commit_sha: str, token: str) -> bool:
    status, data = _api_request(
        f"{GITHUB_API}/repos/{repo}/git/refs/heads/{branch}",
        "PATCH",
        {"sha": commit_sha, "force": False},
        token,
    )
    return status == 200


def push_content_folder(repo: str, branch: str, content_dir: Path, message: str, token: str, log_fn=None) -> bool:
    def log(msg):
        if log_fn:
            log_fn(msg)

    log(f"Fetching default branch for {repo}...")
    branch = get_default_branch(repo, token) or branch

    log(f"Getting current HEAD ref...")
    head_sha = get_ref_sha(repo, branch, token)
    if not head_sha:
        log("ERROR: Could not get HEAD ref. Check repo/token.")
        return False

    log(f"Getting base tree...")
    base_tree = get_commit_tree(repo, head_sha, token)
    if not base_tree:
        log("ERROR: Could not get base tree.")
        return False

    log(f"Scanning content directory: {content_dir}")
    all_files = []
    for root, dirs, files in os.walk(str(content_dir)):
        for fn in files:
            fp = Path(root) / fn
            rel = fp.relative_to(content_dir).as_posix()
            all_files.append((rel, fp))

    log(f"Creating blobs for {len(all_files)} files...")
    blobs = []
    for rel, fp in all_files:
        try:
            raw = fp.read_bytes()
            encoded = base64.b64encode(raw).decode("ascii")
            sha_status, sha_data = _api_request(
                f"{GITHUB_API}/repos/{repo}/git/blobs",
                "POST",
                {"content": encoded, "encoding": "base64"},
                token,
            )
            if sha_status == 201:
                blobs.append({
                    "path": f"content/{rel}",
                    "mode": "100644",
                    "type": "blob",
                    "sha": sha_data["sha"],
                })
            else:
                log(f"  Failed blob for {rel}")
        except Exception as e:
            log(f"  Error reading {rel}: {e}")

    if not blobs:
        log("No files to push.")
        return False

    log(f"Creating tree ({len(blobs)} entries)...")
    tree_sha = create_tree(repo, base_tree, blobs, token)
    if not tree_sha:
        log("ERROR: Could not create tree.")
        return False

    log("Creating commit...")
    commit_sha = create_commit(repo, tree_sha, head_sha, message, token)
    if not commit_sha:
        log("ERROR: Could not create commit.")
        return False

    log("Updating branch reference...")
    if update_ref(repo, branch, commit_sha, token):
        log("DONE: Files pushed to GitHub. Deploy will start shortly.")
        return True
    else:
        log("ERROR: Could not update branch ref.")
        return False
