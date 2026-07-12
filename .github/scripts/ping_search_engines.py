"""
ScholarScript Search Engine Pinger
Pings major search engines daily to index new content.
Runs in GitHub Actions at 12PM IST.
"""
import json
import httpx
from pathlib import Path
from datetime import datetime

SITE_URL = "https://dasguptateach-web.github.io/ScholarScript"
SITEMAP_URL = f"{SITE_URL}/sitemap.xml"
LOG_DIR = Path(".promotion-logs")
LOG_DIR.mkdir(exist_ok=True)

SERVICES = []

def check_indexnow():
    results = []
    urls = [SITE_URL, f"{SITE_URL}/papers/", f"{SITE_URL}/videos/", f"{SITE_URL}/tests/"]
    payload = {
        "host": "dasguptateach-web.github.io",
        "key": "scholarscript-indexnow",
        "keyLocation": f"{SITE_URL}/scholarscript-indexnow.txt",
        "urlList": urls,
    }
    try:
        r = httpx.post("https://api.indexnow.org/indexnow", json=payload, timeout=30)
        results.append(("IndexNow", r.status_code, "OK" if r.status_code == 202 else str(r.text[:100])))
    except Exception as e:
        results.append(("IndexNow", 0, str(e)))
    try:
        r = httpx.get(f"https://www.bing.com/indexnow?url={SITE_URL}&key=scholarscript-indexnow", timeout=30)
        results.append(("Bing IndexNow", r.status_code, "OK" if r.status_code == 202 else str(r.text[:100])))
    except Exception as e:
        results.append(("Bing IndexNow", 0, str(e)))
    return results

def check_yandex():
    results = []
    try:
        r = httpx.get(f"https://webmaster.yandex.com/ping?sitemap={SITEMAP_URL}", timeout=30)
        results.append(("Yandex", r.status_code, "OK" if r.status_code == 200 else str(r.text[:100])))
    except Exception as e:
        results.append(("Yandex", 0, str(e)))
    return results

def check_qwant():
    results = []
    try:
        r = httpx.get(f"https://www.qwant.com/ping?sitemap={SITEMAP_URL}", timeout=30)
        results.append(("Qwant", r.status_code, "OK" if r.status_code == 200 else str(r.text[:100])))
    except Exception as e:
        results.append(("Qwant", 0, str(e)))
    return results

def archive_wayback():
    results = []
    urls_to_save = [
        SITE_URL,
        f"{SITE_URL}/papers/",
        f"{SITE_URL}/videos/",
        f"{SITE_URL}/tests/",
        f"{SITE_URL}/sitemap.xml",
        f"{SITE_URL}/rss.xml",
    ]
    for url in urls_to_save:
        try:
            r = httpx.get(f"https://web.archive.org/save/{url}", timeout=60, follow_redirects=True)
            results.append((f"Wayback: {url}", r.status_code, "Saved"))
        except Exception as e:
            results.append((f"Wayback: {url}", 0, str(e)[:100]))
    return results

def check_commoncrawl():
    results = []
    try:
        r = httpx.get(f"https://index.commoncrawl.org/submit?url={SITE_URL}", timeout=30)
        results.append(("CommonCrawl", r.status_code, str(r.text[:100])))
    except Exception as e:
        results.append(("CommonCrawl", 0, str(e)[:100]))
    return results

def main():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    all_results = []

    print(f"=== ScholarScript Search Engine Pinger ===\n{now}\n")
    all_results.extend(check_indexnow())
    all_results.extend(check_yandex())
    all_results.extend(check_qwant())
    all_results.extend(archive_wayback())
    all_results.extend(check_commoncrawl())

    # Log results
    log = {
        "timestamp": now,
        "results": [{"service": s, "status": c, "message": m} for s, c, m in all_results],
    }
    log_file = LOG_DIR / "ping-results.json"
    with open(log_file, "w") as f:
        json.dump(log, f, indent=2)

    # Print summary
    success = sum(1 for _, c, _ in all_results if c and 200 <= c < 400)
    total = len(all_results)
    print(f"\nResults: {success}/{total} successful")
    for s, c, m in all_results:
        status = "OK" if c and 200 <= c < 400 else "FAIL"
        print(f"  [{status}] {s}: {c} — {m[:80]}")

if __name__ == "__main__":
    main()
