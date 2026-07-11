"""
ScholarScript Social Media Promoter
Auto-posts new content to Twitter, Bluesky, and Mastodon.
Set API keys as GitHub Secrets for the promote.yml workflow.
"""
import os
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime, timezone

SITE_URL = os.environ.get("SITE_URL", "https://dasguptateach-web.github.io/ScholarScript")
STATE_FILE = Path(".social-state.json")

def get_site_title():
    import yaml
    cfg = Path("config.yaml")
    if cfg.exists():
        with open(cfg) as f:
            data = yaml.safe_load(f) or {}
        return data.get("site", {}).get("title", "ScholarScript")
    return "ScholarScript"

def extract_content_items():
    items = []
    content_dir = Path("content")
    if not content_dir.exists():
        print("No content/ directory found")
        return items
    for subdir in ("papers", "videos", "creative-writing", "external-links"):
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
                    import yaml
                    try:
                        meta = yaml.safe_load(parts[1]) or {}
                    except Exception:
                        meta = {}
                    body = parts[2]
            title = meta.get("title", f.stem.replace("-", " ").title())
            tags = meta.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            summary = meta.get("summary", "") or body.strip()[:200]
            item_type = meta.get("type", subdir.rstrip("s").rstrip("-link"))
            author = meta.get("author", "")
            og_image = meta.get("og_image", "")
            items.append({
                "title": title,
                "slug": meta.get("slug", f.stem),
                "type": item_type,
                "tags": tags,
                "summary": summary,
                "author": author,
                "date": str(meta.get("date", "")),
                "og_image": og_image,
            })
    return items

def load_posted():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}

def save_posted(posted):
    STATE_FILE.write_text(json.dumps(posted, indent=2))

def item_id(item):
    return hashlib.md5(f"{item['slug']}-{item['date']}".encode()).hexdigest()

def make_post_text(item, site_title):
    type_emoji = {"paper": "", "video": "", "creative-writing": "", "external-link": ""}
    type_label = {"paper": "Scholarly Paper", "video": "Video", "creative-writing": "Creative Writing", "external-link": "Resource"}
    emoji = type_emoji.get(item["type"], "")
    label = type_label.get(item["type"], item["type"])
    tags_str = " ".join(f"#{re.sub(r'[^a-zA-Z0-9]', '', t)}" for t in item["tags"][:4]) if item["tags"] else ""
    author_str = f" by {item['author']}" if item["author"] else ""
    url = f"{SITE_URL}/{item['type']}/{item['slug']}/"
    text = f'{emoji} {label}: "{item["title"]}"{author_str}\n\n{item["summary"][:200]}\n\n{url}\n\n{tags_str}'
    text = text.replace("\\", " ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def post_to_bluesky(text):
    handle = os.environ.get("BLUESKY_HANDLE")
    password = os.environ.get("BLUESKY_PASSWORD")
    if not handle or not password:
        print("Bluesky credentials not configured, skipping")
        return False
    import httpx
    try:
        resp = httpx.post(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": password},
            timeout=30,
        )
        if resp.status_code != 200:
            return False
        session = resp.json()
        access_jwt = session["accessJwt"]
        did = session["did"]
        post_resp = httpx.post(
            "https://bsky.social/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {access_jwt}"},
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": {
                    "text": text[:300],
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                },
            },
            timeout=30,
        )
        print(f"Bluesky response: {post_resp.status_code}")
        return post_resp.status_code == 200
    except Exception as e:
        print(f"Bluesky post failed: {e}")
        return False

def post_to_twitter(text):
    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_secret = os.environ.get("TWITTER_ACCESS_SECRET")
    if not all([api_key, api_secret, access_token, access_secret]):
        print("Twitter credentials not configured, skipping")
        return False
    try:
        import httpx
        import base64
        # OAuth 1.0a — simplified; use tweepy for production
        bearer = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
        token_resp = httpx.post(
            "https://api.twitter.com/oauth2/token",
            headers={"Authorization": f"Basic {bearer}"},
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        if token_resp.status_code != 200:
            print(f"Twitter auth failed: {token_resp.status_code}")
            return False
        token = token_resp.json().get("access_token")
        post_resp = httpx.post(
            "https://api.twitter.com/2/tweets",
            headers={"Authorization": f"Bearer {token}"},
            json={"text": text[:280]},
            timeout=30,
        )
        print(f"Twitter response: {post_resp.status_code}")
        return post_resp.status_code == 201
    except Exception as e:
        print(f"Twitter post failed: {e}")
        return False

def post_to_mastodon(text):
    return False
    instance = os.environ.get("MASTODON_INSTANCE", "").rstrip("/")
    token = os.environ.get("MASTODON_TOKEN")
    if not instance or not token:
        print("Mastodon credentials not configured, skipping")
        return False
    import httpx
    try:
        resp = httpx.post(
            f"{instance}/api/v1/statuses",
            headers={"Authorization": f"Bearer {token}"},
            data={"status": text[:500]},
            timeout=30,
        )
        print(f"Mastodon response: {resp.status_code}")
        return resp.status_code == 200
    except Exception as e:
        print(f"Mastodon post failed: {e}")
        return False

def main():
    site_title = get_site_title()
    items = extract_content_items()
    if not items:
        print("No content items found")
        return
    posted = load_posted()
    to_post = []
    for item in items:
        iid = item_id(item)
        if iid not in posted:
            to_post.append(item)
    if not to_post:
        print("No new content to promote")
        return
    for item in to_post[:3]:
        iid = item_id(item)
        text = make_post_text(item, site_title)
        print(f"\nPosting: {item['title']}")
        posted_bs = post_to_bluesky(text)
        posted_tw = post_to_twitter(text)
        posted_any = posted_bs or posted_tw
        if posted_any:
            posted[iid] = {
                "title": item["title"],
                "slug": item["slug"],
                "date": item["date"],
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "bluesky": posted_bs,
                "twitter": posted_tw,
            }
            platforms = "Bluesky" + (" + Twitter" if posted_tw else "")
            print(f"  Posted to {platforms}")
        else:
            print(f"  Skipped (no platform configured)")
            posted[iid] = {
                "title": item["title"],
                "slug": item["slug"],
                "date": item["date"],
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "skipped": True,
            }
        save_posted(posted)

if __name__ == "__main__":
    main()
