import requests, os, base64, json
token = os.environ['GITHUB_TOKEN']
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
r = requests.get('https://api.github.com/repos/dasguptateach-web/ScholarScript/contents/.github/workflows/deploy.yml', headers=headers)
if r.status_code == 200:
    content = base64.b64decode(r.json()['content']).decode()
    print(content)
else:
    print(f'Error: {r.status_code} {r.text[:200]}')

# Also try triggering without inputs
r2 = requests.post('https://api.github.com/repos/dasguptateach-web/ScholarScript/actions/workflows/deploy.yml/dispatches',
    headers=headers, json={'ref': 'main'})
print(f'\nTrigger without inputs: {r2.status_code}')
if r2.status_code != 204:
    print(f'Error: {r2.text[:200]}')
