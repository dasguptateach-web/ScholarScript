"""
ScholarScript Directory Submitter
Submits the site to free educational directories and listing services.
Runs daily at 12PM IST via GitHub Actions.
"""
import json
import httpx
from pathlib import Path
from datetime import datetime

SITE_URL = "https://dasguptateach-web.github.io/ScholarScript"
SITEMAP_URL = f"{SITE_URL}/sitemap.xml"
LOG_DIR = Path(".promotion-logs")
LOG_DIR.mkdir(exist_ok=True)

DIRECTORIES = [
    # Educational & Academic directories
    ("OER Commons (search presence)", f"https://www.oercommons.org/browse?f.keyword=English+Literature", "GET"),
    ("Base (Bielefeld Academic Search)", f"https://www.base-search.net/about/en/suggest.php?url={SITE_URL}", "GET"),
    ("UK Web Archive", f"https://www.webarchive.org.uk/en/ukwa/add?url={SITE_URL}", "GET"),
    # RSS Readers
    ("Feedly", f"https://feedly.com/i/subscription/feed/{SITE_URL}/rss.xml", "GET"),
    ("The Old Reader", f"https://theoldreader.com/feeds/subscribe?url={SITE_URL}/rss.xml", "GET"),
    # Social bookmarking
    ("Pinboard", f"https://pinboard.in/add?url={SITE_URL}&title=ScholarScript+Free+English+Literature", "GET"),
    # Student resources
    ("StudentVIP", f"https://studentvip.com/submit?url={SITE_URL}", "GET"),
    ("Lekture", f"https://lekture.com/submit?url={SITE_URL}", "GET"),
]

def ping_service(name, url, method):
    try:
        if method == "GET":
            r = httpx.get(url, timeout=30, follow_redirects=True)
            return (name, r.status_code, "Reached" if r.status_code < 400 else str(r.status_code))
        elif method == "POST":
            r = httpx.post(url, timeout=30)
            return (name, r.status_code, "Reached" if r.status_code < 400 else str(r.status_code))
    except httpx.TimeoutException:
        return (name, 0, "Timeout")
    except Exception as e:
        return (name, 0, str(e)[:100])

def main():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"=== ScholarScript Directory Submitter ===\n{now}\n")

    results = []
    for name, url, method in DIRECTORIES:
        result = ping_service(name, url, method)
        results.append(result)
        status = "OK" if result[1] and result[1] < 400 else "FAIL"
        print(f"  [{status}] {result[0]}: {result[1]}")

    log = {
        "timestamp": now,
        "results": [{"service": s, "status": c, "message": m} for s, c, m in results],
    }
    with open(LOG_DIR / "directory-submissions.json", "w") as f:
        json.dump(log, f, indent=2)

    success = sum(1 for _, c, _ in results if c and c < 400)
    print(f"\nDone: {success}/{len(results)} directories reached")

if __name__ == "__main__":
    main()
