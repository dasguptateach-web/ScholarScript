import requests, sys, time
token = sys.argv[1]
repo = sys.argv[2]

# Check builds
r = requests.get(f'https://api.github.com/repos/{repo}/pages/builds', headers={'Authorization': f'token {token}'})
builds = r.json()
for b in builds[:8]:
    commit = b['commit'][:8]
    status = b['status']
    err = b.get('error', {}).get('message', '')
    created = b['created_at']
    print(f'{commit} {status} err={err} {created}')

# Check raw content of deployed page
r2 = requests.get(f'https://raw.githubusercontent.com/{repo}/main/paper/modernist-imagery/index.html', headers={'Authorization': f'token {token}'})
c = r2.text
print(f'\nRaw file: tts-lang-label={("tts-lang-label" in c)}')
print(f'googleTranslateElementInit={("googleTranslateElementInit" in c)}')
print(f'activeLang={("activeLang" in c)}')

# Keep checking until build completes
print('\nWaiting for build to finish...')
for i in range(20):
    time.sleep(10)
    r = requests.get(f'https://api.github.com/repos/{repo}/pages/builds', headers={'Authorization': f'token {token}'})
    b = r.json()[0]
    status = b['status']
    commit = b['commit'][:8]
    print(f'  [{i*10}s] {commit} {status}')
    if status in ('built', 'errored'):
        # Check live
        r3 = requests.get('https://dasguptateach-web.github.io/ScholarScript/paper/modernist-imagery/', headers={'Cache-Control': 'no-cache'})
        c3 = r3.text
        print(f'  Live: tts-lang-label={("tts-lang-label" in c3)} googleTranslateElementInit={("googleTranslateElementInit" in c3)}')
        break
