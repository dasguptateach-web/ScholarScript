import requests, os
token = os.environ['GITHUB_TOKEN']
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
r = requests.get('https://api.github.com/repos/dasguptateach-web/ScholarScript/actions/runs?per_page=5', headers=headers)
for run in r.json().get('workflow_runs', []):
    c = run.get("conclusion", "")
    print(f'{run["status"]:>12}/{str(c):>7} - {run["created_at"][:19]} - {run.get("event","?"):>15}')
