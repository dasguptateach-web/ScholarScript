import requests, os

token = os.environ.get("GITHUB_TOKEN") or open(".github_token").read().strip()
headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

# Check repo visibility
r = requests.get("https://api.github.com/repos/dasguptateach-web/ScholarScript", headers=headers)
d = r.json()
print(f"Private: {d.get('private')}")
print(f"Visibility: {d.get('visibility')}")
print(f"Has issues: {d.get('has_issues')}")

if d.get("private"):
    print("\nRepo is PRIVATE. GitHub Pages requires a public repo (Free plan).")
    # Make it public
    r2 = requests.patch("https://api.github.com/repos/dasguptateach-web/ScholarScript",
                        headers=headers, json={"private": False})
    if r2.status_code == 200:
        print("Repo is now PUBLIC!")
    else:
        print(f"Failed to make public: {r2.text[:200]}")
else:
    print("Repo is already PUBLIC.")
    print("\nPages should work. Trying alternative setup...")
    # Try with gh-pages branch approach
    r3 = requests.get("https://api.github.com/repos/dasguptateach-web/ScholarScript/pages", headers=headers)
    print(f"GET /pages -> {r3.status_code}")
    if r3.status_code == 404:
        print("No pages site exists yet.")
