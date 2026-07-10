"""
ScholarScript Repeat Promoter
Re-promotes older content that hasn't been shared recently.
Picks a random older paper/video to reshare each day.
"""
import os
import json
import random
import re
import yaml as pyyaml
import httpx
from pathlib import Path
from datetime import datetime, timezone

SITE_URL = os.environ.get("SITE_URL", "https://dasguptateach-web.github.io/ScholarScript")
STATE_FILE = Path(".repeat-state.json")
LOG_DIR = Path(".promotion-logs")
LOG_DIR.mkdir(exist_ok=True)

def load_all_content():
    items = []
    content_dir = Path("content")
    if not content_dir.exists():
        print("No content/ directory found")
        return items
    for subdir in ("papers", "videos", "creative-writing"):
        d = content_dir / subdir
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            content = f.read_text(encoding="utf-8")
            meta = {}
            body = content
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    try:
                        meta = pyyaml.safe_load(parts[1]) or {}
                    except Exception:
                        meta = {}
                    body = parts[2]
            title = meta.get("title", f.stem.replace("-", " ").title())
            tags = meta.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            summary = meta.get("summary", "") or body.strip()[:200]
            item_type = meta.get("type", subdir.rstrip("s"))
            items.append({
                "title": title,
                "slug": meta.get("slug", f.stem),
                "type": item_type,
                "tags": tags,
                "summary": summary,
                "author": meta.get("author", ""),
                "date": str(meta.get("date", "")),
                "file": str(f),
            })
    return items

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def make_post_text(item):
    type_emoji = {"paper": "", "video": "", "creative-writing": ""}
    type_label = {"paper": "Paper", "video": "Video", "creative-writing": "Writing"}
    emoji = type_emoji.get(item["type"], "")
    label = type_label.get(item["type"], item["type"])
    tags = " ".join(f"#{re.sub(r'[^a-zA-Z0-9]', '', t)}" for t in item["tags"][:3])
    author = f" by {item['author']}" if item["author"] else ""
    url = f"{SITE_URL}/{item['type']}/{item['slug']}/"
    text = f'{emoji} ScholarScript {label}: "{item["title"]}"{author}\n\n{item["summary"][:180]}\n\n{url}\n{tags}'
    return text[:300]

def post_to_bluesky(text):
    handle = os.environ.get("BLUESKY_HANDLE")
    password = os.environ.get("BLUESKY_PASSWORD")
    if not handle or not password:
        return False
    try:
        resp = httpx.post(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": password},
            timeout=30,
        )
        if resp.status_code != 200:
            return False
        session = resp.json()
        post_resp = httpx.post(
            "https://bsky.social/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {session['accessJwt']}"},
            json={
                "repo": session["did"],
                "collection": "app.bsky.feed.post",
                "record": {
                    "text": text[:300],
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                },
            },
            timeout=30,
        )
        return post_resp.status_code == 200
    except Exception as e:
        print(f"  Bluesky error: {e}")
        return False

def post_to_twitter(text):
    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_secret = os.environ.get("TWITTER_ACCESS_SECRET")
    if not all([api_key, api_secret, access_token, access_secret]):
        return False
    try:
        import base64
        bearer = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
        token_resp = httpx.post(
            "https://api.twitter.com/oauth2/token",
            headers={"Authorization": f"Basic {bearer}"},
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        if token_resp.status_code != 200:
            return False
        token = token_resp.json().get("access_token")
        post_resp = httpx.post(
            "https://api.twitter.com/2/tweets",
            headers={"Authorization": f"Bearer {token}"},
            json={"text": text[:280]},
            timeout=30,
        )
        return post_resp.status_code == 201
    except Exception as e:
        print(f"  Twitter error: {e}")
        return False

def main():
    print("=== ScholarScript Repeat Promoter ===")
    items = load_all_content()
    if not items:
        print("No content found")
        return

    state = load_state()
    posted_slugs = set(state.get("posted", []))
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Find items not posted in the last 7 days
    available = [i for i in items if i["slug"] not in posted_slugs]
    if not available:
        # Reset if all posted
        posted_slugs = set()
        available = items
        print("All content has been posted, resetting cycle")

    # Pick up to 2 items to repromote
    picks = random.sample(available, min(2, len(available)))
    for item in picks:
        text = make_post_text(item)
        print(f"\nRe-promoting: {item['title']}")
        bs = post_to_bluesky(text)
        tw = post_to_twitter(text)
        if bs or tw:
            posted_slugs.add(item["slug"])
            platforms = []
            if bs: platforms.append("Bluesky")
            if tw: platforms.append("Twitter")
            print(f"  Posted to {' + '.join(platforms)}")
        else:
            print(f"  Skipped (no credentials)")
            posted_slugs.add(item["slug"])

    state["posted"] = list(posted_slugs)
    state["last_run"] = date
    save_state(state)

    log = {"timestamp": datetime.utcnow().isoformat(), "repeated": [i["title"] for i in picks]}
    with open(LOG_DIR / "repeat-log.json", "w") as f:
        json.dump(log, f, indent=2)
    print(f"\nDone. Re-shared {len(picks)} items")

if __name__ == "__main__":
    main()
