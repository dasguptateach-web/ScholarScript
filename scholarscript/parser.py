import re
import frontmatter
import markdown
from pathlib import Path
from typing import List, Optional, Tuple
from .models import ContentItem


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def parse_content_file(filepath: Path) -> Optional[ContentItem]:
    """Parse a single .md file with YAML front matter into a ContentItem."""
    try:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            post = frontmatter.load(f)
    except Exception:
        return None

    meta = post.metadata
    body = post.content

    rel_path = filepath.relative_to(filepath.parents[2] if len(filepath.parents) > 2 else filepath.parent)
    content_type = _detect_type(filepath)

    title = meta.get("title", filepath.stem.replace("-", " ").title())
    date = meta.get("date", _extract_date_from_path(filepath))
    if hasattr(date, 'strftime'):
        date = date.strftime("%Y-%m-%d")
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    html = markdown.markdown(
        body,
        extensions=["extra", "codehilite", "toc", "sane_lists"],
    )

    word_count = len(body.split())
    reading_time = max(1, round(word_count / 200))

    item = ContentItem(
        title=title,
        slug=meta.get("slug", slugify(title)),
        type=content_type,
        date=date,
        tags=tags,
        author=meta.get("author"),
        author_email=meta.get("author_email"),
        paypal=meta.get("paypal"),
        paper_url=meta.get("paper_url"),
        video_url=meta.get("video_url"),
        external_url=meta.get("external_url"),
        pen_name=meta.get("pen_name"),
        genre=meta.get("genre"),
        cover_image=meta.get("cover_image"),
        summary=meta.get("summary", body[:200].strip() + "..." if len(body) > 200 else body.strip()),
        body_html=html,
        body_md=body,
        word_count=word_count,
        reading_time=reading_time,
        og_image=meta.get("og_image"),
        canonical_url=meta.get("canonical_url"),
        hreflang=meta.get("hreflang"),
        ebook_url=meta.get("ebook_url"),
    )
    return item


def _detect_type(path: Path) -> str:
    parent = path.parent.name.lower()
    if "creative" in parent or "fiction" in parent:
        return "creative-writing"
    if "video" in parent:
        return "video"
    if "external" in parent or "link" in parent:
        return "external-link"
    if "paper" in parent:
        return "paper"
    return "paper"


def _extract_date_from_path(path: Path) -> str:
    from datetime import datetime
    try:
        mtime = path.stat().st_mtime
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def load_all_content(content_dir: Path) -> Tuple[List[ContentItem], List[ContentItem], List[ContentItem], List[ContentItem]]:
    papers, videos, creative, external = [], [], [], []
    for subdir, bucket in [("papers", papers), ("videos", videos),
                            ("creative-writing", creative), ("external-links", external)]:
        d = content_dir / subdir
        if d.exists():
            for f in d.glob("*.md"):
                item = parse_content_file(f)
                if item:
                    bucket.append(item)
            bucket.sort(key=lambda i: i.date, reverse=True)
    return papers, videos, creative, external
