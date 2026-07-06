import requests, os
token = os.environ['GITHUB_TOKEN']
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
repo = 'dasguptateach-web/ScholarScript'

# Check Pages config
r = requests.get(f'https://api.github.com/repos/{repo}/pages', headers=headers)
pages = r.json()
print(f'build_type: {pages.get("build_type")}')
print(f'status: {pages.get("status")}')
print(f'html_url: {pages.get("html_url")}')
print(f'url: {pages.get("url")}')
print(f'cname: {pages.get("cname")}')
print(f'source: {pages.get("source")}')

# Check pages deployments
r = requests.get(f'https://api.github.com/repos/{repo}/pages/deployments', headers=headers)
if r.status_code == 200:
    deploys = r.json()
    print(f'\nDeployments: {len(deploys)}')
    for d in deploys[-3:]:
        print(f'  Created: {d.get("created_at","?")}')
        print(f'  Status: {d.get("status","?")}')
        print(f'  Artifact URL: {d.get("artifact_url","?")}')
else:
    print(f'\nPages deployments: {r.status_code}')
    print(r.text[:200])
