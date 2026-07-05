import requests, sys, time

token = sys.argv[1]
repo = sys.argv[2]

print("Waiting for Pages build...")
for i in range(15):
    time.sleep(8)
    r = requests.get(f'https://api.github.com/repos/{repo}/pages/builds', headers={'Authorization': f'token {token}'})
    b = r.json()[0]
    status = b['status']
    commit = b['commit'][:8]
    err = b['error']['message'] if b.get('error') else None
    print(f'  [{i*8}s] {commit} {status} err={err}')
    if status in ('built', 'errored'):
        break

r2 = requests.get('https://dasguptateach-web.github.io/ScholarScript/paper/modernist-imagery/', headers={'Cache-Control': 'no-cache'})
has_tts = 'tts-voice' in r2.text
has_synth_cancel = 'synth.cancel()' in r2.text
has_try_catch = 'try {' in r2.text
print(f'\nLive: tts-voice={has_tts} synth.cancel={has_synth_cancel} try-catch={has_try_catch}')
