import requests, sys
token = sys.argv[1]
repo = sys.argv[2]
builds = requests.get(f'https://api.github.com/repos/{repo}/pages/builds', headers={'Authorization': f'token {token}'}).json()
for b in builds[:5]:
    commit = b['commit'][:8]
    status = b['status']
    created = b['created_at']
    print(f'{commit} {status} {created}')
r = requests.get('https://dasguptateach-web.github.io/ScholarScript/paper/modernist-imagery/', headers={'Cache-Control': 'no-cache'})
c = r.text
print(f'\nLive: __ttsLang from dropdown = {"window.__ttsLang = lang" in c}')
