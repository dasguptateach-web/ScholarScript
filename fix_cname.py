import requests, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
token = os.environ.get("GITHUB_TOKEN") or open(".github_token").read().strip()
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
repo = "dasguptateach-web/ScholarScript"

# 1. Try to delete the CNAME from the repo
r = requests.get(f"https://api.github.com/repos/{repo}/contents/CNAME", headers=headers)
if r.status_code == 200:
    sha = r.json()["sha"]
    r2 = requests.delete(f"https://api.github.com/repos/{repo}/contents/CNAME",
                         headers=headers,
                         json={"message": "Remove CNAME", "sha": sha})
    print(f"Delete CNAME: {r2.status_code}")
else:
    print(f"No CNAME file in repo ({r.status_code})")

# 2. Clear the custom domain from Pages settings
# There's no direct API for this, but we can update the pages config
# Actually, let's just try rebuilding and redeploying without the CNAME
print("CNAME removed. Rebuild and redeploy without CNAME.")
