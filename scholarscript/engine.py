import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from jinja2 import Environment, FileSystemLoader

from .config import Config
from .models import ContentItem
from .parser import load_all_content
from .plugins import load_plugins
from .seo import generate_sitemap, generate_rss, generate_robots


class Engine:
    """Core static site generation engine."""

    def __init__(self, config: Config):
        self.config = config
        self.items: List[ContentItem] = []
        self.plugins = load_plugins(
            config.get_plugin_dir(),
            config.site.plugins_enabled,
        )

        # Set up Jinja2
        theme_dir = config.get_theme_dir()
        templates_dir = theme_dir
        if not templates_dir.exists():
            templates_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True,
        )
        self.env.globals.update({
            "site": config.site,
            "base_url": config.get_base_url(),
            "now": datetime.now(),
        })

    def build(self):
        """Full site build."""
        # Load content
        papers, videos, creative, external = load_all_content(self.config.get_content_dir())
        self.items = papers + videos + creative + external
        tests = self._load_tests()
        self.env.globals.update({
            "papers": papers,
            "videos": videos,
            "creative": creative,
            "links": external,
            "tests": tests,
        })

        # Plugin: on_content_loaded
        for p in self.plugins:
            p.on_content_loaded(self.items)

        # Plugin: on_build_start
        for p in self.plugins:
            p.on_build_start(self.config, self.items)

        public_dir = self.config.get_public_dir()

        # Clean public dir
        if public_dir.exists():
            shutil.rmtree(str(public_dir))
        public_dir.mkdir(parents=True)

        # Copy static assets
        theme_dir = self.config.get_theme_dir()
        if theme_dir.exists():
            for sub in ("css", "js", "img"):
                src = theme_dir / sub
                if src.exists():
                    dst = public_dir / sub
                    shutil.copytree(str(src), str(dst), dirs_exist_ok=True)

        # Build tag index
        tag_map = self._build_tag_map()

        # Load author-of-month
        author_of_month = self._load_author_of_month()

        # Render pages
        self._render_index(public_dir, papers, videos, creative, external, author_of_month)
        self._render_archive(public_dir, "papers", papers, "Papers")
        self._render_archive(public_dir, "videos", videos, "Videos")
        self._render_archive(public_dir, "creative-writing", creative, "Creative Writing")
        self._render_archive(public_dir, "external-links", external, "External Links")
        self._render_tags(public_dir, tag_map)
        self._render_author_of_month(public_dir, author_of_month)
        self._render_donate(public_dir)
        self._render_submit(public_dir)
        self._render_health(public_dir)
        self._render_tests_archive(public_dir, tests)

        # Render individual content pages
        for item in self.items:
            self._render_content(public_dir, item, tag_map)

        # Render test pages
        for test in tests:
            self._render_test_page(public_dir, test)

        # SEO files
        generate_sitemap(self.items, self.config.get_base_url(),
                         str(public_dir / "sitemap.xml"))
        generate_rss(self.items, self.config.site,
                     str(public_dir / "rss.xml"))
        generate_robots(f"{self.config.get_base_url()}/sitemap.xml",
                        str(public_dir / "robots.txt"))

        # Render CNAME if custom domain
        if self.config.site.domain and "github" not in self.config.site.domain:
            with open(public_dir / "CNAME", "w") as f:
                f.write(self.config.site.domain)

        # Generate search index
        self._generate_search_index(public_dir)

        # Create .nojekyll for GitHub Pages
        (public_dir / ".nojekyll").write_text("")

        # Plugin: on_build_end
        for p in self.plugins:
            p.on_build_end(public_dir)

    def _render(self, template_name: str, context: dict, output_path: Path):
        """Render a single template and write to output_path."""
        ctx = context.copy()
        for p in self.plugins:
            ctx = p.on_page_render(template_name, ctx)
        try:
            html = self.env.get_template(template_name).render(ctx)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
        except Exception:
            pass

    def _render_index(self, public_dir, papers, videos, creative, external, aom):
        ctx = {
            "papers": papers,
            "videos": videos,
            "creative": creative,
            "links": external,
            "author_of_month": aom,
            "page_title": "Home",
            "page_url": self.config.get_base_url() + "/",
            "page_ogtype": "website",
        }
        self._render("index.html", ctx, public_dir / "index.html")

    def _render_archive(self, public_dir, content_type, items, title):
        ctx = {
            "items": items,
            "page_title": title,
            "content_type": content_type,
            "page_url": self.config.get_base_url() + "/" + content_type + "/",
            "page_ogtype": "website",
        }
        self._render("archive.html", ctx, public_dir / content_type / "index.html")

    def _render_content(self, public_dir, item, tag_map):
        related = tag_map.get(item.slug, [])[:3]
        base = self.config.get_base_url()
        page_url = f"{base}/{item.type}/{item.slug}/"
        ctx = {
            "item": item,
            "related": related,
            "page_title": item.title,
            "page_description": item.summary,
            "page_url": page_url,
            "page_image": item.og_image,
            "page_canonical": item.canonical_url,
            "page_ogtype": "article",
        }
        self._render("content.html", ctx, public_dir / item.type / item.slug / "index.html")

    def _render_tags(self, public_dir, tag_map):
        all_tags = {}
        for item in self.items:
            for tag in item.tags:
                if tag not in all_tags:
                    all_tags[tag] = []
                all_tags[tag].append(item)
        ctx = {
            "tags": all_tags,
            "page_title": "Tags",
            "page_url": self.config.get_base_url() + "/tags/",
            "page_ogtype": "website",
        }
        self._render("tags.html", ctx, public_dir / "tags" / "index.html")

    def _build_tag_map(self) -> dict:
        tag_map = {}
        for item in self.items:
            seen = set()
            related = []
            for other in self.items:
                if other.slug == item.slug:
                    continue
                if other.slug in seen:
                    continue
                if set(other.tags) & set(item.tags):
                    related.append(other)
                    seen.add(other.slug)
            tag_map[item.slug] = related
        return tag_map

    def _load_author_of_month(self) -> Optional[dict]:
        path = self.config.get_data_dir() / "author-of-month.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _render_author_of_month(self, public_dir, aom):
        ctx = {
            "author": aom,
            "page_title": "Author of the Month",
            "page_url": self.config.get_base_url() + "/author-of-month/",
            "page_ogtype": "website",
        }
        self._render("author-of-month.html", ctx, public_dir / "author-of-month" / "index.html")

    def _render_donate(self, public_dir):
        ctx = {
            "page_title": "Support ScholarScript",
            "page_url": self.config.get_base_url() + "/donate/",
            "page_ogtype": "website",
        }
        self._render("donate.html", ctx, public_dir / "donate" / "index.html")

    def _render_submit(self, public_dir):
        ctx = {
            "page_title": "Submit Creative Writing",
            "page_url": self.config.get_base_url() + "/creative-writing/submit/",
            "page_ogtype": "website",
        }
        self._render("submit-writing.html", ctx, public_dir / "creative-writing" / "submit" / "index.html")

    def _generate_search_index(self, public_dir):
        idx = []
        for item in self.items:
            idx.append({
                "title": item.title,
                "slug": item.slug,
                "type": item.type,
                "summary": (item.summary or "")[:300],
                "tags": item.tags,
                "date": item.date,
                "author": item.author or "",
                "url": f"/{item.type}/{item.slug}/",
            })
        for test in self.env.globals.get("tests", []):
            idx.append({
                "title": test.get("title", ""),
                "slug": test.get("slug", ""),
                "type": "test",
                "summary": test.get("description", "")[:300],
                "tags": ["test", "mcq", "practice"],
                "date": test.get("date", ""),
                "author": "",
                "url": f"/test/{test.get('slug', '')}/",
            })
        path = public_dir / "search-index.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(idx, f, ensure_ascii=False)

    def _render_health(self, public_dir):
        ctx = {
            "page_title": "Financial Health",
            "prize_amount": self.config.site.prize_amount,
            "hidden": True,
            "page_url": self.config.get_base_url() + "/health/",
            "page_ogtype": "website",
        }
        self._render("health.html", ctx, public_dir / "health" / "index.html")

    def _load_tests(self) -> list:
        tests_dir = self.config.get_data_dir() / "tests"
        tests = []
        if not tests_dir.exists():
            return tests
        for f in sorted(tests_dir.glob("*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                tests.append(data)
            except Exception:
                pass
        tests.sort(key=lambda t: t.get("date", ""), reverse=True)
        return tests

    def _render_test_page(self, public_dir, test_data):
        slug = test_data.get("slug", "unknown")
        ctx = {
            "test_slug": slug,
            "test_json": json.dumps(test_data, ensure_ascii=False),
            "test_email": self.config.site.owner_email or "",
            "page_title": test_data.get("title", "Test"),
            "page_description": test_data.get("description", f"Practice test with {test_data.get('total_questions', 0)} questions"),
            "page_url": self.config.get_base_url() + "/test/" + slug + "/",
            "page_ogtype": "website",
        }
        self._render("test.html", ctx, public_dir / "test" / slug / "index.html")

    def _render_tests_archive(self, public_dir, tests):
        ctx = {
            "tests": tests,
            "page_title": "Interactive Tests",
            "page_url": self.config.get_base_url() + "/tests/",
            "page_ogtype": "website",
        }
        self._render("tests.html", ctx, public_dir / "tests" / "index.html")
