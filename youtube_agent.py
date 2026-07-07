"""
YouTube Agent for ScholarScript — v2.0 (Auto-Pipeline)
Auto-discovers best English YouTube video for papers.
Usage:
  python youtube_agent.py                   # Scan all papers missing videos
  python youtube_agent.py --overwrite       # Re-scan all papers
  python youtube_agent.py --slug <slug>     # Single paper (post-ingest hook)
  python youtube_agent.py --watch           # Continuous watch mode
"""
import json, os, re, sys, subprocess, time, io
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

CONTENT_DIR = Path("content/papers")
VIDEO_DIR = Path("content/videos")
CACHE_FILE = Path("youtube_cache.json")

PAPER_TOPIC_MAP = {
    "victorian-poetry": "Victorian Poetry Tennyson Arnold Browning lecture analysis English literature",
    "ugc-net-english-paper-ii": "UGC NET English Literature paper 2 practice test solved paper",
    "the-solitude-of-alexander-selkirk-as-a-dramatic-monologue": "William Cowper Alexander Selkirk poem dramatic monologue analysis",
    "the-rape-of-the-lock-cantos-13": "Rape of the Lock Pope mock epic analysis Cantos 1-3 English literature",
    "the-elizabethan-age": "Elizabethan Age English Literature history lecture university",
    "study-guide-of-the-castle-of-otranto-with-special-focus-on-supernaturalism": "Castle of Otranto Gothic novel Walpole supernatural analysis English",
    "study-guide-jk-rowling-harry-potter-and-the-philosophers-stone": "Harry Potter Philosopher Stone JK Rowling study guide analysis English",
    "structuralism": "Structuralism literary theory Saussure lecture English criticism",
    "sophocles-oedipus": "Sophocles Oedipus Rex tragedy analysis lecture English literature",
    "shakespeare-tempest": "Tempest Shakespeare postcolonial colonial discourse analysis English",
    "shakespeare-and-his-plays": "William Shakespeare all plays overview biography English literature lecture",
    "prakarana-the-little-clay-cart-mricchakatika": "Mrichchhakatika Little Clay Cart Sudraka Sanskrit drama English analysis",
    "postmodern-narrative": "postmodern literature narrative theory identity fragmentation lecture English",
    "mricchakatika-social-criticism": "Mricchakatika Little Clay Cart social criticism Sudraka analysis English",
    "mock-epic": "mock epic Pope Rape of the Lock satirical poetry analysis English",
    "marxism-study-guide": "Marxist literary theory criticism introduction study guide English",
    "marxism-short-notes": "Marxist literary criticism theory key concepts English literature",
    "literary-criticism-and-theory-for-ugc-net": "Literary criticism theory UGC NET English literature complete",
    "last-of-the-mohicans-study-guide": "Last of the Mohicans James Fenimore Cooper summary analysis",
    "kadambari": "Kadambari Banabhatta Sanskrit romance literature analysis English",
    "indian-classical-literature-the-little-clay-cart-mricchakatika-sat": "Indian classical literature Mricchakatika Sanskrit drama English study",
    "harry-satqa": "Harry Potter analysis themes characters English literature",
    "film-adaptations-of-shakespeare-reinventing-the-bard-on-screen": "Shakespeare film adaptations cinema analysis English lecture",
    "ecocriticism-a-study": "Ecocriticism literature environment nature Cheryll Glotfelty English",
    "classical-drama": "Classical Greek Roman drama influence Elizabethan theatre English",
    "charudutta-the-little-clay-cart-mricchakatika": "Charudatta character Mricchakatika Sanskrit drama English literature",
    "blood-and-betrayal-in-mumbai-vishal-bhardwajs-maqbool-as-a-cinematic-reinvention-of-macbeth": "Maqbool Vishal Bhardwaj Macbeth adaptation film analysis English",
    "bertolt-brecht-the-good-woman-of-setzuan": "Bertolt Brecht Good Woman of Setzuan epic theatre analysis English",
    "belinda": "Belinda character Pope Rape of the Lock analysis English literature",
}

TEST_PAPERS = {"auto-deploy-final-test", "final-integrated-test", "ppt"}
NON_EN_PATTERNS = re.compile(r'(in hindi|in bengali|in tamil|in telugu|in marathi|in urdu|in malayalam|in kannada|in gujarati|in punjabi|हिंदी|বাংলা|தமிழ்|hindi\s|bengali\s|coaching|adda247)', re.I)
EN_KEYWORDS = ["lecture", "analysis", "english", "explained", "introduction", "study", "guide", "literature", "criticism", "summary", "history", "course", "university", "college", "lesson"]

def parse_front_matter(text):
    parts = text.split("---", 2)
    if len(parts) < 3: return {}, text
    try:
        import yaml
        meta = yaml.safe_load(parts[1]) or {}
    except Exception:
        meta = {}
    return meta, parts[2] if len(parts) > 2 else ""

def search_youtube(query, max_results=3):
    if not query: return []
    cmd = ["yt-dlp", "--flat-playlist", "--dump-json", f"ytsearch{max_results}:{query}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        results = []
        for line in result.stdout.strip().split("\n"):
            if not line: continue
            data = json.loads(line)
            results.append({
                "id": data["id"],
                "title": data.get("title", ""),
                "channel": data.get("channel", ""),
                "views": data.get("view_count", 0) or 0,
                "duration": data.get("duration", 0) or 0,
                "description": (data.get("description") or "")[:200],
            })
        results.sort(key=lambda x: x["views"], reverse=True)
        return results
    except: return []

def pick_best_video(results, paper_title):
    scored = []
    for r in results:
        t = (r["title"] + " " + r.get("description", "")).lower()
        tw = set(re.findall(r'\w+', t))
        pw = set(re.findall(r'\w+', paper_title.lower()))
        overlap = len(tw & pw)
        en_penalty = 1000 if NON_EN_PATTERNS.search(t) else 0
        en_bonus = sum(2 for kw in EN_KEYWORDS if kw in t)
        r["relevance"] = overlap + en_bonus + (r["views"] / 100000) - en_penalty
        scored.append(r)
    scored.sort(key=lambda x: x["relevance"], reverse=True)
    best = scored[0] if scored else None
    if best:
        dl = best.get("description", "").lower()
        if NON_EN_PATTERNS.search(dl):
            for r in scored[1:]:
                if not NON_EN_PATTERNS.search(r.get("description", "").lower()):
                    best = r; break
    return best

def generate_video_md(paper_slug, video, paper_title, paper_tags, summary):
    vid_id = video["id"]
    video_url = f"https://www.youtube.com/watch?v={vid_id}"
    date_str = datetime.now().strftime("%Y-%m-%d")
    author = video.get("channel", "YouTube Scholar")
    desc = video.get("description", "") or ""
    content = f"""---
title: "{paper_title}"
date: {date_str}
type: video
author: "{author}"
tags: [{', '.join(paper_tags[:5])}]
video_url: "{video_url}"
summary: "{summary or desc[:160]}"
---

# {paper_title}

{video["title"]}

**Channel:** {video["channel"]}  
**Views:** {video['views']:,}  
**Duration:** {video['duration']//60}:{video['duration']%60:02d}

{desc}
"""
    filepath = VIDEO_DIR / f"{paper_slug}.md"
    filepath.write_text(content, encoding="utf-8")
    return filepath

def process_paper(slug, pf, cache, overwrite=False):
    """Process a single paper: find video and create markdown."""
    if slug in TEST_PAPERS:
        return {"status": "skipped", "reason": "test paper"}

    vid_path = VIDEO_DIR / f"{slug}.md"
    if vid_path.exists() and not overwrite:
        return {"status": "skipped", "reason": "video exists"}

    topic = PAPER_TOPIC_MAP.get(slug, slug.replace("-", " ") + " English literature lecture")
    text = pf.read_text(encoding="utf-8")
    meta, _ = parse_front_matter(text)
    paper_title = meta.get("title", slug)
    tags = meta.get("tags", [slug])
    summary = meta.get("summary", f"A video lecture on {paper_title}")

    if slug in cache:
        results = [cache[slug]]
    else:
        results = search_youtube(topic)
        if not results:
            results = search_youtube(f"{' '.join(tags[:3])} English literature")
        if results:
            cache[slug] = results[0]

    best = pick_best_video(results, paper_title) if results else None
    if not best:
        return {"status": "failed", "reason": "no video found", "slug": slug}

    fp = generate_video_md(slug, best, paper_title, tags, summary)
    safe = best['title'][:60].encode('ascii', 'replace').decode('ascii')
    print(f"  [{slug}] -> {best['id']} ({safe}) [{best['views']:,} views]")
    return {"status": "created", "slug": slug, "id": best["id"], "file": str(fp)}

def main():
    overwrite = "--overwrite" in sys.argv
    single_slug = None
    watch_mode = "--watch" in sys.argv

    for i, arg in enumerate(sys.argv):
        if arg == "--slug" and i + 1 < len(sys.argv):
            single_slug = sys.argv[i + 1]

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    cache = {}
    if CACHE_FILE.exists():
        cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))

    if watch_mode:
        print("YouTube Agent Watch Mode — monitoring for new papers every 30s")
        known = set(f.stem for f in VIDEO_DIR.glob("*.md"))
        while True:
            for pf in sorted(CONTENT_DIR.glob("*.md")):
                slug = pf.stem
                vid_path = VIDEO_DIR / f"{slug}.md"
                if slug in known or slug in TEST_PAPERS:
                    continue
                if not vid_path.exists():
                    print(f"\n[WATCH] New paper detected: {slug}")
                    result = process_paper(slug, pf, cache, overwrite=False)
                    print(f"  Result: {result['status']}")
                    known.add(slug)
                    CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
            time.sleep(30)
        return

    if single_slug:
        pf = CONTENT_DIR / f"{single_slug}.md"
        if not pf.exists():
            print(f"Paper '{single_slug}' not found")
            return
        result = process_paper(single_slug, pf, cache, overwrite=overwrite)
        print(f"Result: {result['status']}")
        CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        return

    # Full scan
    paper_files = sorted(CONTENT_DIR.glob("*.md"))
    print(f"Found {len(paper_files)} papers\n")
    results = []
    for pf in paper_files:
        slug = pf.stem
        r = process_paper(slug, pf, cache, overwrite=overwrite)
        results.append(r)
        time.sleep(0.5)

    CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    created = sum(1 for r in results if r["status"] == "created")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    failed = sum(1 for r in results if r["status"] == "failed")
    print(f"\nDone! Created: {created}, Skipped: {skipped}, Failed: {failed}")

if __name__ == "__main__":
    main()
