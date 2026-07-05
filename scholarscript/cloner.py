import os
import re
import time
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Optional

import requests
from bs4 import BeautifulSoup, Comment

from .models import CloneProfile
from .parser import slugify


class WebsiteCloner:
    """Clones websites into Markdown content for ScholarScript."""

    def __init__(self, profile: CloneProfile):
        self.profile = profile
        self.visited: set = set()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": profile.user_agent})
        self.domain = ""

    def clone(self, target_url: str, output_dir: Path) -> dict:
        """Clone a website into the output directory."""
        parsed = urlparse(target_url)
        self.domain = parsed.netloc

        site_name = slugify(parsed.netloc + parsed.path.replace("/", "-"))
        site_dir = output_dir / site_name
        site_dir.mkdir(parents=True, exist_ok=True)

        assets_dir = site_dir / "assets"
        assets_dir.mkdir(exist_ok=True)

        if self.profile.respect_robots:
            robots_url = urljoin(target_url, "/robots.txt")
            try:
                resp = self.session.get(robots_url, timeout=10)
                if resp.status_code == 200:
                    disallowed = self._parse_robots(resp.text)
                    # Store disallowed paths for later use
                    self._disallowed = disallowed
            except Exception:
                self._disallowed = []
        else:
            self._disallowed = []

        self._crawl_and_convert(target_url, site_dir, assets_dir, depth=0)

        # Generate index file
        index_path = site_dir / "index.md"
        items = list(site_dir.glob("*.md"))
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"title: \"Cloned: {target_url}\"\n")
            f.write(f"date: {time.strftime('%Y-%m-%d')}\n")
            f.write(f"type: paper\n")
            f.write(f"tags: [cloned, {self.domain.replace('.', '-')}]\n")
            f.write(f"source_url: \"{target_url}\"\n")
            f.write("---\n\n")
            f.write(f"# Cloned Site: {target_url}\n\n")
            f.write(f"Pages cloned: {len(items)}\n\n")
            for item in sorted(items):
                if item.name == "index.md":
                    continue
                with open(item, "r", encoding="utf-8") as sf:
                    front = sf.read(500)
                    title_match = re.search(r'title:\s*"([^"]+)"', front)
                    title = title_match.group(1) if title_match else item.stem
                    f.write(f"- [{title}]({item.name})\n")

        return {
            "site": site_name,
            "pages": len(self.visited),
            "output": str(site_dir),
        }

    def _crawl_and_convert(self, url: str, site_dir: Path, assets_dir: Path, depth: int):
        if depth > 2:
            return
        if url in self.visited:
            return
        if len(self.visited) >= self.profile.max_pages:
            return

        for pat in self.profile.exclude_patterns:
            if pat in url:
                return

        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc != self.domain:
            return

        self.visited.add(url)
        time.sleep(self.profile.delay)

        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
        except Exception:
            return

        # Check content type
        ct = resp.headers.get("Content-Type", "")
        if "text/html" not in ct and "application/xhtml" not in ct:
            return

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove unwanted elements
        for sel in self.profile.strip_selectors:
            for el in soup.select(sel):
                el.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
            comment.extract()

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else parsed.path or "Untitled"
        title = re.sub(r'\s+', ' ', title).strip()

        # Get main content
        for tag in ["article", "main", ".content", "#content", ".post", ".entry"]:
            main = soup.select_one(tag)
            if main:
                break
        else:
            main = soup.find("body") or soup

        # Convert to markdown
        md_content = self._html_to_markdown(str(main), assets_dir, url)

        slug = slugify(title)[:60]
        page_path = site_dir / f"{slug}.md"

        with open(page_path, "w", encoding="utf-8") as f:
            f.write("---\n")
            f.write(f"title: \"{title}\"\n")
            f.write(f"date: {time.strftime('%Y-%m-%d')}\n")
            f.write(f"type: paper\n")
            f.write(f"source_url: \"{url}\"\n")
            f.write(f"source_domain: \"{self.domain}\"\n")
            f.write("---\n\n")
            f.write(md_content)

        # Crawl links
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if not href or href.startswith("#") or href.startswith("mailto:"):
                continue
            abs_url = urljoin(url, href)
            if self.domain in abs_url:
                self._crawl_and_convert(abs_url, site_dir, assets_dir, depth + 1)

    def _html_to_markdown(self, html: str, assets_dir: Path, base_url: str) -> str:
        """Simple HTML to Markdown conversion."""
        soup = BeautifulSoup(html, "html.parser")

        lines = []
        for el in soup.descendants:
            if isinstance(el, Comment):
                continue
            if el.name == "h1":
                lines.append(f"# {el.get_text(strip=True)}")
                lines.append("")
            elif el.name == "h2":
                lines.append(f"## {el.get_text(strip=True)}")
                lines.append("")
            elif el.name == "h3":
                lines.append(f"### {el.get_text(strip=True)}")
                lines.append("")
            elif el.name == "h4":
                lines.append(f"#### {el.get_text(strip=True)}")
                lines.append("")
            elif el.name == "p":
                text = el.get_text(strip=True)
                if text:
                    lines.append(text)
                    lines.append("")
            elif el.name in ("ul", "ol"):
                for li in el.find_all("li", recursive=False):
                    prefix = "- " if el.name == "ul" else "1. "
                    text = li.get_text(strip=True)
                    if text:
                        lines.append(f"{prefix}{text}")
                lines.append("")
            elif el.name == "blockquote":
                for child in el.find_all("p"):
                    text = child.get_text(strip=True)
                    if text:
                        lines.append(f"> {text}")
                lines.append("")
            elif el.name == "a" and el.get("href"):
                text = el.get_text(strip=True)
                href = el["href"]
                if text and href and not href.startswith("#"):
                    lines.append(f"[{text}]({href})")
            elif el.name == "img" and el.get("src"):
                src = el["src"]
                alt = el.get("alt", "image")
                if self.profile.include_images:
                    local_path = self._download_asset(src, assets_dir, base_url)
                    lines.append(f"![{alt}]({local_path})")
                    lines.append("")

        return "\n".join(lines)

    def _download_asset(self, src: str, assets_dir: Path, base_url: str) -> str:
        """Download image/assets and return local path."""
        try:
            url = urljoin(base_url, src)
            parsed = urlparse(url)
            if not parsed.netloc:
                url = urljoin(base_url, src)
            ext = os.path.splitext(parsed.path)[1] or ".jpg"
            name = slugify(parsed.path) + ext
            local = assets_dir / name

            if not local.exists():
                r = self.session.get(url, timeout=15)
                if r.status_code == 200:
                    with open(local, "wb") as f:
                        f.write(r.content)

            return f"assets/{name}"
        except Exception:
            return src

    def _parse_robots(self, text: str) -> list:
        disallowed = []
        for line in text.split("\n"):
            line = line.strip()
            if line.lower().startswith("disallow:"):
                path = line.split(":", 1)[1].strip()
                if path:
                    disallowed.append(path)
        return disallowed
