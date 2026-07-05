import requests, re, time

url = "https://dasguptateach-web.github.io/ScholarScript/"
print(f"Checking {url}...")

for i in range(6):
    try:
        r = requests.get(url, timeout=10, allow_redirects=True)
        print(f"Attempt {i+1}: Status {r.status_code}")
        if r.status_code == 200:
            m = re.search(r"<title>(.*?)</title>", r.text, re.DOTALL)
            title = m.group(1) if m else "N/A"
            print(f"SITE IS LIVE!")
            print(f"Title: {title}")
            print(f"URL: {r.url}")
            break
    except Exception as e:
        print(f"Attempt {i+1}: {e}")
    if i < 5:
        time.sleep(5)
else:
    print("Site not ready yet. GitHub Pages can take up to 2 minutes on first deploy.")
