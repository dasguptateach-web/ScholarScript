import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from .models import SiteConfig


def get_top_author_pages(config: SiteConfig, data_dir: Path, month: Optional[str] = None) -> dict:
    """
    Retrieve aggregated pageview data from GoatCounter JSON export.
    Falls back to local JSON if no API available.
    """
    if month is None:
        month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    goatcounter_file = data_dir / f"goatcounter_{month}.json"
    if not goatcounter_file.exists():
        return _simulate_pageviews(data_dir, month)

    try:
        with open(goatcounter_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return _simulate_pageviews(data_dir, month)

    author_views = {}
    for entry in data:
        path = entry.get("path", "")
        count = entry.get("count", 0)
        if "/creative-writing/" in path:
            author = _author_from_path(path)
            if author:
                author_views[author] = author_views.get(author, 0) + count

    return author_views


def _author_from_path(path: str) -> Optional[str]:
    parts = path.strip("/").split("/")
    if len(parts) >= 2:
        return parts[1]
    return None


def _simulate_pageviews(data_dir: Path, month: str) -> dict:
    """Fallback: read local author-page-view log."""
    log_file = data_dir / "pageviews.json"
    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def record_pageview(data_dir: Path, path: str, author: str):
    log_file = data_dir / "pageviews.json"
    try:
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
        if author not in data:
            data[author] = 0
        data[author] += 1
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
