"""
ScholarScript Social Post Generator
Generates copy-paste posts for Reddit, LinkedIn, Facebook, Twitter, and email newsletters.
Outputs markdown files to social-posts/ directory.
"""
import os
import re
import yaml
import json
from pathlib import Path
from datetime import datetime

SITE_URL = os.environ.get("SITE_URL", "https://dasguptateach-web.github.io/ScholarScript")
OUTPUT_DIR = Path("social-posts")
OUTPUT_DIR.mkdir(exist_ok=True)

def load_content():
    items = []
    content_dir = Path("content")
    if not content_dir.exists():
        print("No content/ directory found, using sample data")
        return []
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
            items.append({
                "title": title,
                "slug": meta.get("slug", f.stem),
                "type": item_type,
                "tags": tags,
                "summary": summary,
                "author": author,
                "date": str(meta.get("date", "")),
            })
    return items

def make_reddit_post(item):
    type_label = {"paper": "Scholarly Paper", "video": "Video Lecture", "creative-writing": "Creative Work", "external-link": "Resource"}
    label = type_label.get(item["type"], item["type"])
    url = f"{SITE_URL}/{item['type']}/{item['slug']}/"
    return f"""{label}: "{item['title']}"

{item['summary'][:300]}

Read more: {url}

{' | '.join(f'#{t}' for t in item['tags'][:5])}
"""

def make_linkedin_post(item):
    type_label = {"paper": "scholarly paper", "video": "video lecture", "creative-writing": "creative work", "external-link": "resource"}
    label = type_label.get(item["type"], item["type"])
    url = f"{SITE_URL}/{item['type']}/{item['slug']}/"
    author = f" by {item['author']}" if item['author'] else ""
    return f"""New {label}{author}: "{item['title']}"

{item['summary'][:400]}

Read the full article for free: {url}

#{' #'.join(t.replace(' ', '').replace('-', '') for t in item['tags'][:8])}
#ScholarScript #EnglishLiterature #FreeEducation"""

def make_twitter_post(item):
    type_emoji = {"paper": "", "video": "", "creative-writing": "", "external-link": ""}
    type_label = {"paper": "Paper", "video": "Video", "creative-writing": "Writing", "external-link": "Resource"}
    emoji = type_emoji.get(item["type"])
    label = type_label.get(item["type"], item["type"])
    url = f"{SITE_URL}/{item['type']}/{item['slug']}/"
    tags = " ".join(f"#{re.sub(r'[^a-zA-Z0-9]', '', t)}" for t in item['tags'][:3])
    text = f'{emoji} {label}: "{item["title"]}"\n\n{item["summary"][:150]}\n\n{url}\n{tags}'
    return text[:280]

def make_email_newsletter(items):
    now = datetime.now().strftime("%B %d, %Y")
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>ScholarScript Monthly - {now}</title></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
<h1>ScholarScript Monthly</h1>
<p>New resources added this week on ScholarScript — your free English Literature hub.</p>
<hr>"""
    for item in items[:10]:
        url = f"{SITE_URL}/{item['type']}/{item['slug']}/"
        type_badge = item["type"].replace("-", " ").title()
        tags = ", ".join(f"#{t}" for t in item["tags"][:3])
        html += f"""
<div style="margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #eee;">
<h2><a href="{url}" style="color:#7c3aed;">{item['title']}</a></h2>
<p style="color:#666; font-size:14px;">{type_badge} | {item['date']}{f' | by {item["author"]}' if item['author'] else ''}</p>
<p>{item['summary'][:200]}</p>
<p style="font-size:13px; color:#999;">{tags}</p>
<a href="{url}" style="display:inline-block;background:#7c3aed;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none;">Read More</a>
</div>"""
    html += """
<hr>
<p style="color:#999; font-size:12px;">ScholarScript — Free English Literature resources. Forever.</p>
</body>
</html>"""
    return html

def main():
    items = load_content()
    if not items:
        print("No content found, nothing to generate")
        return

    # Reddit post
    with open(OUTPUT_DIR / f"reddit-post-{datetime.now().strftime('%Y-%m-%d')}.md", "w", encoding="utf-8") as f:
        f.write(make_reddit_post(items[0]))
        f.write("\n---\n\n### Suitable subreddits:\n")
        f.write("- r/AskLiteraryStudies\n- r/literature\n- r/englishliterature\n- r/shakespeare\n- r/ELATeachers\n- r/HomeworkHelp\n- r/books\n- r/academia\n")
        f.write("- r/UGCNet\n- r/Indian_Academia\n")

    # LinkedIn post
    with open(OUTPUT_DIR / f"linkedin-post-{datetime.now().strftime('%Y-%m-%d')}.md", "w", encoding="utf-8") as f:
        f.write(make_linkedin_post(items[0]))

    # Twitter posts
    tweets = []
    for item in items[:5]:
        tweets.append(f"--- Tweet {items.index(item)+1} ---\n{make_twitter_post(item)}\n\n")
    with open(OUTPUT_DIR / f"twitter-thread-{datetime.now().strftime('%Y-%m-%d')}.md", "w", encoding="utf-8") as f:
        f.writelines(tweets)

    # Email newsletter
    with open(OUTPUT_DIR / f"newsletter-{datetime.now().strftime('%Y-%m-%d')}.html", "w", encoding="utf-8") as f:
        f.write(make_email_newsletter(items))

    print(f"Generated social posts for {len(items)} items in {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
