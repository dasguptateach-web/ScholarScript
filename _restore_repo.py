import requests, os, base64, json, mimetypes
from pathlib import Path

token = os.environ['GITHUB_TOKEN']
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
repo = 'dasguptateach-web/ScholarScript'
root = Path(r'C:\Users\81\AppData\Local\Temp\opencode\ScholarScript')

exclude_dirs = {'public', 'uploads', '__pycache__', '.git', 'Lib', 'scholarscript.egg-info', 'node_modules', '.github_token', '.github_repo', '_check_workflow.py', '_restore_repo.py'}
exclude_exts = {'.pyc', '.pyo', '.lock'}
exclude_files = {'.github_token', '.github_repo', 'desktop-drop.log'}

def should_include(path):
    rel = path.relative_to(root)
    parts = rel.parts
    for p in parts:
        if p in exclude_dirs or p.startswith('_'):
            return False
    if rel.name in exclude_files:
        return False
    if rel.suffix in exclude_exts:
        return False
    return True

# Collect all files to include
files = []
for f in sorted(root.rglob('*')):
    if f.is_file() and should_include(f):
        rel = f.relative_to(root).as_posix()
        files.append((rel, f))

print(f'Total files to push: {len(files)}')

# Get current head
r = requests.get(f'https://api.github.com/repos/{repo}/git/refs/heads/main', headers=headers)
parent_sha = r.json()['object']['sha']
print(f'Parent commit: {parent_sha[:12]}')

# Create blobs for all files and build tree
tree = []
for i, (rel_path, file_path) in enumerate(files):
    content = file_path.read_bytes()
    r = requests.post(f'https://api.github.com/repos/{repo}/git/blobs',
        headers=headers, json={'content': base64.b64encode(content).decode(), 'encoding': 'base64'})
    if r.status_code not in (201, 200):
        print(f'Failed to create blob for {rel_path}: {r.status_code} {r.text[:100]}')
        continue
    blob_sha = r.json()['sha']
    tree.append({'path': rel_path, 'mode': '100644', 'type': 'blob', 'sha': blob_sha})
    if (i+1) % 20 == 0:
        print(f'  Processed {i+1}/{len(files)}')

print(f'Creating tree with {len(tree)} entries...')
r = requests.post(f'https://api.github.com/repos/{repo}/git/trees',
    headers=headers, json={'tree': tree})
if r.status_code not in (200, 201):
    print(f'Failed to create tree: {r.status_code} {r.text[:200]}')
    exit(1)
tree_sha = r.json()['sha']

# Create commit
commit_msg = 'Restore source code with all papers'
r = requests.post(f'https://api.github.com/repos/{repo}/git/commits',
    headers=headers, json={'message': commit_msg, 'tree': tree_sha, 'parents': [parent_sha]})
if r.status_code not in (200, 201):
    print(f'Failed to create commit: {r.status_code} {r.text[:200]}')
    exit(1)
commit_sha = r.json()['sha']

# Update branch (force to replace broken state)
r = requests.patch(f'https://api.github.com/repos/{repo}/git/refs/heads/main',
    headers=headers, json={'sha': commit_sha, 'force': True})
if r.status_code in (200, 201):
    print(f'Success! Branch main updated to {commit_sha[:12]}')
    print('Workflow will trigger automatically on push.')
else:
    print(f'Failed: {r.status_code} {r.text[:200]}')
