"""
ScholarScript Facebook Auto-Poster
Posts new content to Facebook Page via Graph API.
Requires FACEBOOK_PAGE_TOKEN secret set in GitHub.
"""

import os, json, hashlib, urllib.request, urllib.parse, urllib.error
from pathlib import Path
from datetime import datetime, timezone

SITE_URL = os.environ.get("SITE_URL", "https://dasguptateach-web.github.io/ScholarScript")
PAGE_ID = "61592063721692"
STATE_FILE = Path(".facebook-state.json")

try:
    import yaml
except ImportError:
    yaml = None

def load_content():
    items = []
    content_dir = Path("content")
    if not content_dir.exists():
        return items
    for subdir in ("papers", "videos", "creative-writing", "external-links", "tests"):
        d = content_dir / subdir
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            content = f.read_text(encoding="utf-8")
            meta = {}
            body = content
            if content.startswith("---") and yaml:
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    try:
                        meta = yaml.safe_load(parts[1]) or {}
                    except:
                        meta = {}
                    body = parts[2]
            title = meta.get("title", f.stem.replace("-", " ").title())
            tags = meta.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            summary = meta.get("summary", "") or body.strip()[:250]
            item_type = meta.get("type", subdir.rstrip("s").rstrip("-link"))
            items.append({
                "title": title,
                "slug": meta.get("slug", f.stem),
                "type": item_type,
                "tags": tags[:4],
                "summary": summary[:300],
                "author": meta.get("author", ""),
                "date": str(meta.get("date", "")),
            })
    return items

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            return {"posted": {}}
    return {"posted": {}}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def item_id(item):
    raw = f"{item['slug']}-{item['date']}"
    return hashlib.md5(raw.encode()).hexdigest()

TYPE_LABELS = {
    "paper": "Scholarly Paper",
    "video": "Video Lecture",
    "test": "Practice Test",
    "creative-writing": "Creative Writing",
    "external-link": "External Resource",
}

TYPE_EMOJI = {
    "paper": "",
    "video": "",
    "test": "",
    "creative-writing": "",
    "external-link": "",
}

def post_to_facebook(token, page_id, message, link):
    url = f"https://graph.facebook.com/v22.0/{page_id}/feed"
    data = {"message": message[:63206], "link": link, "access_token": token}
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  Facebook API error {e.code}: {e.read().decode()[:300]}")
        return None

def main():
    print("ScholarScript Facebook Auto-Poster")
    print(f"  Page ID: {PAGE_ID}")
    
    token = os.environ.get("FACEBOOK_PAGE_TOKEN")
    if not token:
        print("  SKIP — FACEBOOK_PAGE_TOKEN not set")
        print("  To get one:")
        print("  1. Go to https://developers.facebook.com/apps/")
        print("  2. Create an app → Add Facebook Pages API")
        print("  3. Generate a Page Access Token")
        print("  4. Add as GitHub Secret: FACEBOOK_PAGE_TOKEN")
        return
    
    items = load_content()
    print(f"  Found {len(items)} content items")
    
    state = load_state()
    posted = state.get("posted", {})
    
    new_items = [i for i in items if item_id(i) not in posted]
    print(f"  New items to post: {len(new_items)}")
    
    if not new_items:
        print("  Nothing new.")
        return
    
    for item in new_items[:3]:
        iid = item_id(item)
        label = TYPE_LABELS.get(item["type"], item["type"])
        emoji = TYPE_EMOJI.get(item["type"], "")
        author = f" by {item['author']}" if item["author"] else ""
        url = f"{SITE_URL}/{item['type']}/{item['slug']}/"
        
        message = f"{emoji} {label}: {item['title']}{author}\n\n"
        message += f"{item['summary'][:200]}\n\n"
        message += f"Free English Literature resources — no signup required.\n{SITE_URL}"
        
        result = post_to_facebook(token, PAGE_ID, message, url)
        if result and "id" in result:
            print(f"  [{iid}] Posted: {item['title']}")
            posted[iid] = {
                "title": item["title"],
                "slug": item["slug"],
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "post_id": result["id"],
            }
        else:
            print(f"  [{iid}] Failed: {item['title']}")
            posted[iid] = {
                "title": item["title"],
                "slug": item["slug"],
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "failed": True,
            }
        save_state({"posted": posted})
    
    print(f"  Done. Total posted: {len(posted)}")

if __name__ == "__main__":
    main()
