"""
ScholarScript Marketing Agent
Fully autonomous multi-platform promoter.
Discovers new content, posts everywhere, pings search engines, generates drafts.
"""

import os, sys, json, hashlib, re, hmac, base64, urllib.request, urllib.parse
from pathlib import Path
from datetime import datetime, timezone
from html import escape

SITE_URL = os.environ.get("SITE_URL", "https://dasguptateach-web.github.io/ScholarScript")
SITE_NAME = os.environ.get("SITE_NAME", "ScholarScript")
STATE_FILE = Path(".marketing-state.json")
DRAFTS_DIR = Path("social-posts")
DRAFTS_DIR.mkdir(exist_ok=True)

try:
    import yaml
except ImportError:
    yaml = None

# ─── Content Discovery ─────────────────────────────────────────────

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
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3 and yaml:
                    try:
                        meta = yaml.safe_load(parts[1]) or {}
                    except Exception:
                        meta = {}
                    body = parts[2]
            title = meta.get("title", f.stem.replace("-", " ").title())
            tags = meta.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            summary = meta.get("summary", "") or re.sub(r'[#*_\[\]`>\|]', '', body.strip()[:250])
            item_type = meta.get("type", subdir.rstrip("s").rstrip("-link"))
            items.append({
                "title": title,
                "slug": meta.get("slug", f.stem),
                "type": item_type,
                "tags": tags[:6],
                "summary": summary,
                "author": meta.get("author", ""),
                "date": str(meta.get("date", "")),
                "og_image": meta.get("og_image", ""),
                "source_file": str(f),
            })
    return items

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {"posted": {}, "indexed": {}}
    return {"posted": {}, "indexed": {}}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))

def item_id(item):
    raw = f"{item['slug']}-{item['date']}-{item['type']}"
    return hashlib.md5(raw.encode()).hexdigest()

# ─── Post Text Generation ──────────────────────────────────────────

TYPE_META = {
    "paper":               {"emoji": "", "label": "Scholarly Paper"},
    "video":               {"emoji": "", "label": "Video Lecture"},
    "creative-writing":    {"emoji": "", "label": "Creative Writing"},
    "test":                {"emoji": "", "label": "Practice Test"},
    "external-link":       {"emoji": "", "label": "External Resource"},
}

def make_post_texts(item):
    meta = TYPE_META.get(item["type"], {"emoji": "", "label": item["type"]})
    emoji = meta["emoji"]
    label = meta["label"]
    tags_str = " ".join(f"#{re.sub(r'[^a-zA-Z0-9]', '', t)}" for t in item["tags"][:4]) if item["tags"] else ""
    author_str = f" by {item['author']}" if item["author"] else ""
    url = f"{SITE_URL}/{item['type']}/{item['slug']}/"
    summary = item["summary"][:200]

    # Short tweet/post
    short = f"{emoji} {label}: \"{item['title']}\"{author_str}\n{url}"[:280]

    # Medium post (Bluesky/LinkedIn)
    medium = f"{emoji} {label}: \"{item['title']}\"{author_str}\n\n{summary}\n\n{url}\n\n{tags_str}"
    medium = re.sub(r'\s+', ' ', medium).strip()

    # Long-form Reddit post
    long = f"# {item['title']}\n\n**{label}**{author_str}\n\n{summary}\n\nFull article: {url}\n\n---\n\n*Automatically shared from {SITE_NAME}*"

    return {"short": short[:280], "medium": medium[:500], "long": long[:2000]}

# ─── Platform Posters ──────────────────────────────────────────────

def post_to_bluesky(text):
    handle = os.environ.get("BLUESKY_HANDLE")
    password = os.environ.get("BLUESKY_PASSWORD")
    if not handle or not password:
        print("  [Bluesky] SKIP — credentials not set")
        return False
    try:
        import httpx
        resp = httpx.post("https://bsky.social/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": password}, timeout=30)
        if resp.status_code != 200:
            print(f"  [Bluesky] Auth failed: {resp.status_code}")
            return False
        session = resp.json()
        post_resp = httpx.post("https://bsky.social/xrpc/com.atproto.repo.createRecord",
            headers={"Authorization": f"Bearer {session['accessJwt']}"},
            json={"repo": session["did"], "collection": "app.bsky.feed.post",
                  "record": {"text": text[:300], "createdAt": datetime.now(timezone.utc).isoformat()}},
            timeout=30)
        ok = post_resp.status_code == 200
        print(f"  [Bluesky] {'OK' if ok else f'FAIL ({post_resp.status_code})'}")
        return ok
    except Exception as e:
        print(f"  [Bluesky] Error: {e}")
        return False

def post_to_twitter(text):
    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    token = os.environ.get("TWITTER_ACCESS_TOKEN")
    token_secret = os.environ.get("TWITTER_ACCESS_SECRET")
    if not all([api_key, api_secret, token, token_secret]):
        print("  [Twitter] SKIP — credentials not set (need 4 secrets)")
        return False
    try:
        import httpx
        # OAuth 1.0a
        consumer_key = api_key
        consumer_secret = api_secret
        oauth_token = token
        oauth_secret = token_secret

        def oauth_sign(method, url, params):
            sig_parts = {
                "oauth_consumer_key": consumer_key,
                "oauth_nonce": base64.b64encode(os.urandom(32)).decode()[:42],
                "oauth_signature_method": "HMAC-SHA1",
                "oauth_timestamp": str(int(datetime.now().timestamp())),
                "oauth_token": oauth_token,
                "oauth_version": "1.0",
            }
            all_params = {**sig_parts, **params}
            keys = sorted(all_params.keys())
            param_str = "&".join(f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(all_params[k]), safe='')}" for k in keys)
            sig_base = f"{method.upper()}&{urllib.parse.quote(url, safe='')}&{urllib.parse.quote(param_str, safe='')}"
            sig_key = f"{urllib.parse.quote(consumer_secret, safe='')}&{urllib.parse.quote(oauth_secret, safe='')}"
            sig = base64.b64encode(hmac.new(sig_key.encode(), sig_base.encode(), hashlib.sha1).digest()).decode()
            sig_parts["oauth_signature"] = sig
            auth = "OAuth " + ", ".join(f'{k}="{urllib.parse.quote(v, safe="")}"' for k, v in sorted(sig_parts.items()))
            return auth

        tweet_url = "https://api.twitter.com/2/tweets"
        body = json.dumps({"text": text[:280]}).encode()
        auth_header = oauth_sign("POST", tweet_url, json.loads(body))
        resp = httpx.post(tweet_url, content=body,
            headers={"Authorization": auth_header, "Content-Type": "application/json"}, timeout=30)
        ok = resp.status_code in (200, 201)
        print(f"  [Twitter] {'OK' if ok else f'FAIL ({resp.status_code})'}")
        return ok
    except Exception as e:
        print(f"  [Twitter] Error: {e}")
        return False

def post_to_mastodon(text):
    instance = os.environ.get("MASTODON_INSTANCE", "").rstrip("/")
    token = os.environ.get("MASTODON_TOKEN")
    if not instance or not token:
        print("  [Mastodon] SKIP — credentials not set")
        return False
    try:
        import httpx
        resp = httpx.post(f"{instance}/api/v1/statuses",
            headers={"Authorization": f"Bearer {token}"},
            data={"status": text[:500]}, timeout=30)
        ok = resp.status_code == 200
        print(f"  [Mastodon] {'OK' if ok else f'FAIL ({resp.status_code})'}")
        return ok
    except Exception as e:
        print(f"  [Mastodon] Error: {e}")
        return False

def post_to_linkedin(text):
    token = os.environ.get("LINKEDIN_TOKEN")
    author = os.environ.get("LINKEDIN_AUTHOR")
    if not token or not author:
        print("  [LinkedIn] SKIP — credentials not set (need LINKEDIN_TOKEN + LINKEDIN_AUTHOR)")
        return False
    try:
        import httpx
        resp = httpx.post("https://api.linkedin.com/v2/ugcPosts",
            headers={"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0"},
            json={"author": author, "lifecycleState": "PUBLISHED",
                  "specificContent": {"com.linkedin.ugc.ShareContent": {
                      "shareCommentary": {"text": text[:600]},
                      "shareMediaCategory": "NONE"}},
                  "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}},
            timeout=30)
        ok = resp.status_code in (200, 201)
        print(f"  [LinkedIn] {'OK' if ok else f'FAIL ({resp.status_code})'}")
        return ok
    except Exception as e:
        print(f"  [LinkedIn] Error: {e}")
        return False

# ─── Search Engine Indexing ────────────────────────────────────────

def ping_search_engines():
    sitemap_url = f"{SITE_URL}/sitemap.xml"
    engines = {
        "Google":  f"https://www.google.com/ping?sitemap={sitemap_url}",
        "Bing":    f"https://www.bing.com/ping?sitemap={sitemap_url}",
        "IndexNow": "https://api.indexnow.org/indexnow",
    }
    results = {}
    for name, url in engines.items():
        try:
            if name == "IndexNow":
                payload = json.dumps({
                    "host": urllib.parse.urlparse(SITE_URL).hostname,
                    "key": os.environ.get("INDEXNOW_KEY", ""),
                    "keyLocation": f"{SITE_URL}/indexnow-key.txt",
                    "urlList": [SITE_URL],
                }).encode()
                req = urllib.request.Request(url, data=payload,
                    headers={"Content-Type": "application/json"}, method="POST")
            else:
                req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as r:
                results[name] = r.status
            print(f"  [Ping {name}] OK ({results[name]})")
        except Exception as e:
            results[name] = str(e)
            print(f"  [Ping {name}] {e}")
    return results

# ─── Draft Generation ──────────────────────────────────────────────

def generate_drafts(new_items):
    if not new_items:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    draft_file = DRAFTS_DIR / f"posts-{today}.md"
    existing = draft_file.read_text(encoding="utf-8") if draft_file.exists() else ""
    with open(draft_file, "a", encoding="utf-8") as f:
        for item in new_items:
            texts = make_post_texts(item)
            block = f"""
## {item['title']} ({item['type']})
[URL]({SITE_URL}/{item['type']}/{item['slug']}/)

### Twitter / X
{texts['short']}

### Bluesky / Mastodon
{texts['medium']}

### LinkedIn
{texts['medium']}

### Reddit / Facebook
{texts['long']}

---
"""
            if block.strip() not in existing:
                f.write(block)
    print(f"  [Drafts] Appended {len(new_items)} item(s) to {draft_file}")

# ─── Newsletter Generator ──────────────────────────────────────────

def generate_newsletter(all_items):
    recent = [i for i in all_items if i.get("newsletter_sent") != True][:10]
    if not recent:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# {SITE_NAME} — New Content ({today})",
        "",
        f"Here's what's new on {SITE_NAME}:",
        "",
    ]
    for item in recent:
        url = f"{SITE_URL}/{item['type']}/{item['slug']}/"
        lines.append(f"## {item['title']}")
        lines.append(f"*Type: {TYPE_META.get(item['type'], {}).get('label', item['type'])}*")
        if item["author"]:
            lines.append(f"*By: {item['author']}*")
        lines.append("")
        lines.append(item["summary"][:200])
        lines.append("")
        lines.append(f"[Read more]({url})")
        lines.append("")
    lines.append("---")
    lines.append(f"*Automatically generated by {SITE_NAME} Marketing Agent*")
    newsletter = "\n".join(lines)
    nf = DRAFTS_DIR / f"newsletter-{today}.md"
    nf.write_text(newsletter, encoding="utf-8")
    print(f"  [Newsletter] Saved to {nf}")

# ─── Stats Reporter ────────────────────────────────────────────────

def generate_report(state, items):
    posted_count = len(state.get("posted", {}))
    total = len(items)
    report = {
        "total_items": total,
        "posted_count": posted_count,
        "pending": total - posted_count,
        "last_run": datetime.now(timezone.utc).isoformat(),
        "platforms_configured": {
            "bluesky": bool(os.environ.get("BLUESKY_HANDLE")),
            "twitter": bool(os.environ.get("TWITTER_API_KEY")),
            "mastodon": bool(os.environ.get("MASTODON_INSTANCE")),
            "linkedin": bool(os.environ.get("LINKEDIN_TOKEN")),
        }
    }
    report_path = DRAFTS_DIR / "marketing-report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  [Report] Saved to {report_path}")
    print(f"  Total items: {total}, Posted: {posted_count}, Pending: {total - posted_count}")
    return report

# ─── Main ──────────────────────────────────────────────────────────

def main():
    print(f"{'='*50}")
    print(f"  {SITE_NAME} Marketing Agent")
    print(f"  {datetime.now().isoformat()}")
    print(f"{'='*50}")

    items = load_content()
    print(f"\n  Found {len(items)} content items")

    state = load_state()
    posted = state.get("posted", {})

    new_items = [i for i in items if item_id(i) not in posted]
    print(f"  New items to promote: {len(new_items)}")

    if not new_items:
        print("  Nothing new to promote.")
    else:
        for item in new_items[:5]:
            iid = item_id(item)
            texts = make_post_texts(item)
            print(f"\n  ── {item['title']} ({item['type']}) ──")

            results = {}
            results["bluesky"] = post_to_bluesky(texts["medium"])
            results["twitter"] = post_to_twitter(texts["short"])
            results["mastodon"] = post_to_mastodon(texts["medium"])
            results["linkedin"] = post_to_linkedin(texts["medium"])

            posted[iid] = {
                "title": item["title"],
                "slug": item["slug"],
                "type": item["type"],
                "date": item["date"],
                "posted_at": datetime.now(timezone.utc).isoformat(),
                "results": results,
            }
            save_state({"posted": posted, "indexed": state.get("indexed", {})})

    # Generate drafts for all new items
    generate_drafts(new_items)

    # Ping search engines (once per run, not per item)
    print("\n  ── Search Engine Ping ──")
    ping_search_engines()

    # Generate newsletter
    generate_newsletter(items)

    # Report
    generate_report({"posted": posted}, items)

    print(f"\n  Done! {len(new_items)} item(s) processed.")

if __name__ == "__main__":
    main()
