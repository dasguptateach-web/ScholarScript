"""Deploy public/ on top of main branch, preserving existing files."""
import base64, requests, sys
from pathlib import Path

raw = open(".github_token", encoding="utf-8-sig").read().strip()
token = raw.strip()
repo = "dasguptateach-web/ScholarScript"
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

root = Path(".")
public = root / "public"

# Step 1: Get current tree SHA from main branch
r = requests.get(f"https://api.github.com/repos/{repo}/git/refs/heads/main", headers=headers)
if r.status_code != 200:
    print(f"Failed to get branch: {r.status_code}")
    sys.exit(1)
current_commit_sha = r.json()["object"]["sha"]

# Get the current commit to find its tree
r = requests.get(f"https://api.github.com/repos/{repo}/git/commits/{current_commit_sha}", headers=headers)
if r.status_code != 200:
    print(f"Failed to get commit: {r.status_code}")
    sys.exit(1)
base_tree_sha = r.json()["tree"]["sha"]

# Step 2: Collect all public/ files as tree entries
new_entries = []
for f in sorted(public.rglob("*")):
    if f.is_dir():
        continue
    rel = f.relative_to(public).as_posix()
    try:
        content = f.read_bytes().decode("utf-8", errors="replace")
        new_entries.append({"path": rel, "mode": "100644", "type": "blob", "content": content})
    except Exception as e:
        print(f"  Skip {rel}: {e}")

print(f"Adding {len(new_entries)} files from public/ to the existing tree...")

# Step 3: Create a new tree that MERGES with the base tree
# Using base_tree parameter tells GitHub to start from the existing tree
r = requests.post(f"https://api.github.com/repos/{repo}/git/trees", headers=headers, json={
    "base_tree": base_tree_sha,
    "tree": [{"path": e["path"], "mode": e["mode"], "type": e["type"], "content": e["content"]} for e in new_entries]
})
if r.status_code != 201:
    print(f"Tree creation failed: {r.status_code} {r.text[:300]}")
    sys.exit(1)
merged_tree_sha = r.json()["sha"]

# Step 4: Create commit
r = requests.post(f"https://api.github.com/repos/{repo}/git/commits", headers=headers, json={
    "message": "ScholarScript auto-deploy (merged with source files)",
    "tree": merged_tree_sha,
    "parents": [current_commit_sha],
})
if r.status_code != 201:
    print(f"Commit failed: {r.status_code} {r.text[:300]}")
    sys.exit(1)
commit_sha = r.json()["sha"]

# Step 5: Update branch
r = requests.patch(f"https://api.github.com/repos/{repo}/git/refs/heads/main", headers=headers, json={
    "sha": commit_sha, "force": True
})
if r.status_code in (200, 201):
    print(f"Deployed! {len(new_entries)} built files added to main branch.")
    print(f"Commit: {commit_sha[:12]}")
else:
    print(f"Branch update failed: {r.status_code} {r.text[:200]}")

# Step 6: Set Pages source to main branch
r = requests.put(f"https://api.github.com/repos/{repo}/pages", headers=headers, json={
    "source": {"branch": "main", "path": "/"}
})
if r.status_code in (200, 201, 204):
    print("Pages source set to main branch.")
else:
    print(f"Pages config: {r.status_code} {r.text[:200]}")
