import requests, os, sys

token = os.environ.get("GITHUB_TOKEN") or open(".github_token").read().strip()
headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github.v3+json",
}
repo = "dasguptateach-web/ScholarScript"

# Check repo
r = requests.get(f"https://api.github.com/repos/{repo}", headers=headers)
data = r.json()
print(f"Repo: {data.get('full_name')}")
print(f"Branch: {data.get('default_branch')}")
print(f"Has pages: {data.get('has_pages', False)}")

# Try enabling Pages via API
config = {"source": {"branch": "main", "path": "/"}}
r2 = requests.post(f"https://api.github.com/repos/{repo}/pages", headers=headers, json=config)
print(f"POST /pages -> {r2.status_code}")
if r2.status_code == 201:
    print("SUCCESS: GitHub Pages enabled!")
    print(f"Site: https://{repo.split('/')[0]}.github.io/{repo.split('/')[1]}/")
elif r2.status_code == 409:
    print("Pages already exists, updating via PUT...")
    r3 = requests.put(f"https://api.github.com/repos/{repo}/pages", headers=headers, json=config)
    print(f"PUT /pages -> {r3.status_code}")
    if r3.status_code in (200, 204, 201):
        print("SUCCESS: Pages updated!")
    else:
        print(f"PUT failed: {r3.text[:300]}")
elif r2.status_code == 404:
    print("Pages API not available for this repo type.")
    print("Check if the repo has a .gitignore or README (needs at least one commit on main).")
    # Check branch exists
    r_br = requests.get(f"https://api.github.com/repos/{repo}/git/ref/heads/main", headers=headers)
    print(f"Branch check: {r_br.status_code}")
    if r_br.status_code == 404:
        print("Branch 'main' doesn't exist! The repo might be empty.")
        r_br2 = requests.get(f"https://api.github.com/repos/{repo}/git/refs", headers=headers)
        refs = [r['ref'] for r in r_br2.json()] if r_br2.status_code == 200 else []
        print(f"Available refs: {refs}")
else:
    print(f"Response: {r2.text[:300]}")
