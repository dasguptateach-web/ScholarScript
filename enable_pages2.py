import requests, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

token = os.environ.get("GITHUB_TOKEN") or open(".github_token").read().strip()
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
repo = "dasguptateach-web/ScholarScript"

config = {"source": {"branch": "main", "path": "/"}}
r = requests.post(f"https://api.github.com/repos/{repo}/pages", headers=headers, json=config)
print(f"POST -> {r.status_code}")
if r.status_code == 201:
    d = r.json()
    url = d.get("html_url", "https://dasguptateach-web.github.io/ScholarScript/")
    print(f"Pages ENABLED! Site at: {url}")
elif r.status_code == 409:
    print("Already exists, updating...")
    r2 = requests.put(f"https://api.github.com/repos/{repo}/pages", headers=headers, json=config)
    print(f"PUT -> {r2.status_code} {r2.text[:200]}")
else:
    print(r.text[:400])
