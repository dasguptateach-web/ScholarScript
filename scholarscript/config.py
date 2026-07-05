import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from .models import SiteConfig, CloneProfile


DEFAULT_CONFIG = {
    "site": {
        "title": "ScholarScript",
        "tagline": "Scripted for Scholars. Powered by Automation.",
        "domain": "scholarscript.org",
        "base_url": "",
        "author": "ScholarScript Team",
        "language": "en",
        "locale": "en_US",
    },
    "theme": "classic",
    "adsense": {
        "client_id": "",
        "enabled": True,
    },
    "goatcounter": {
        "code": "",
    },
    "resend": {
        "api_key": "",
        "owner_email": "",
    },
    "prize": {
        "amount": 25,
    },
    "ingestion": {
        "auto_ingest": True,
        "schedule": "every 5 minutes",
    },
    "submissions": {
        "auto_mode": True,
    },
    "plugins": {
        "enabled": [],
    },
    "affiliate": {
        "amazon_tag": "",
        "bookshop_id": "",
    },
    "social": {
        "twitter": "",
        "facebook": "",
        "linkedin": "",
        "youtube": "",
        "bluesky": "",
    },
    "hreflang": {},
}


def find_project_root() -> Path:
    """Walk up from cwd to find project root (where config.yaml lives)."""
    cwd = Path.cwd().resolve()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "config.yaml").exists():
            return parent
    return cwd


class Config:
    def __init__(self, path: Optional[Path] = None):
        self.root = (path or find_project_root()).resolve()
        self.config_path = self.root / "config.yaml"
        self._raw: Dict[str, Any] = {}
        self.site = SiteConfig()
        self.clone_profiles: Dict[str, CloneProfile] = {}
        self.load()

    def load(self):
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._raw = yaml.safe_load(f) or {}
        else:
            self._raw = DEFAULT_CONFIG
        self._merge()

    def _merge(self):
        raw = self._raw
        s = raw.get("site", {})
        self.site.title = s.get("title", DEFAULT_CONFIG["site"]["title"])
        self.site.tagline = s.get("tagline", DEFAULT_CONFIG["site"]["tagline"])
        self.site.domain = s.get("domain", DEFAULT_CONFIG["site"]["domain"])
        self.site.base_url = s.get("base_url", DEFAULT_CONFIG["site"]["base_url"])
        self.site.author = s.get("author", DEFAULT_CONFIG["site"]["author"])
        self.site.language = s.get("language", DEFAULT_CONFIG["site"]["language"])
        self.site.locale = s.get("locale", DEFAULT_CONFIG["site"]["locale"])
        self.site.theme = raw.get("theme", DEFAULT_CONFIG["theme"])
        ad = raw.get("adsense", {})
        self.site.adsense_client_id = ad.get("client_id", "")
        self.site.adsense_enabled = ad.get("enabled", True)
        self.site.goatcounter_code = raw.get("goatcounter", {}).get("code", "")
        res = raw.get("resend", {})
        self.site.resend_api_key = res.get("api_key", "")
        self.site.owner_email = res.get("owner_email", "")
        self.site.prize_amount = raw.get("prize", {}).get("amount", 25)
        ing = raw.get("ingestion", {})
        self.site.auto_ingest = ing.get("auto_ingest", True)
        self.site.ingest_schedule = ing.get("schedule", "every 5 minutes")
        self.site.submission_auto_mode = raw.get("submissions", {}).get("auto_mode", True)
        self.site.plugins_enabled = raw.get("plugins", {}).get("enabled", [])
        aff = raw.get("affiliate", {})
        self.site.affiliate_amazon_tag = aff.get("amazon_tag", "")
        self.site.affiliate_bookshop_id = aff.get("bookshop_id", "")
        soc = raw.get("social", {})
        self.site.social_twitter = soc.get("twitter", "")
        self.site.social_facebook = soc.get("facebook", "")
        self.site.social_linkedin = soc.get("linkedin", "")
        self.site.social_youtube = soc.get("youtube", "")
        self.site.social_bluesky = soc.get("bluesky", "")
        self.site.hreflang_alternates = raw.get("hreflang", {})

        # Load clone profiles
        profiles_dir = self.root / "clone_profiles"
        if profiles_dir.exists():
            for f in profiles_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as pf:
                        data = yaml.safe_load(pf) or {}
                    name = f.stem
                    self.clone_profiles[name] = CloneProfile(
                        name=name,
                        include_images=data.get("include_images", True),
                        include_css=data.get("include_css", False),
                        include_js=data.get("include_js", False),
                        max_pages=data.get("max_pages", 50),
                        respect_robots=data.get("respect_robots", True),
                        user_agent=data.get("user_agent", "ScholarScript/1.0"),
                        delay=data.get("delay", 1.0),
                        strip_selectors=data.get("strip_selectors", [
                            "script", "iframe", ".ad", ".adsense", "#google_ads"
                        ]),
                        exclude_patterns=data.get("exclude_patterns", [
                            "/wp-admin", "/login", "/signup"
                        ]),
                    )
                except Exception:
                    pass

    def get_data_dir(self) -> Path:
        d = self.root / "data"
        d.mkdir(exist_ok=True)
        return d

    def get_uploads_dir(self) -> Path:
        d = self.root / "uploads"
        d.mkdir(exist_ok=True)
        (d / "processed").mkdir(exist_ok=True)
        return d

    def get_content_dir(self) -> Path:
        d = self.root / "content"
        d.mkdir(exist_ok=True)
        for sub in ("papers", "videos", "creative-writing", "external-links"):
            (d / sub).mkdir(exist_ok=True)
        return d

    def get_theme_dir(self) -> Path:
        return self.root / "themes" / self.site.theme

    def get_public_dir(self) -> Path:
        d = self.root / "public"
        d.mkdir(exist_ok=True)
        return d

    def get_cloned_dir(self) -> Path:
        d = self.root / "cloned_sites"
        d.mkdir(exist_ok=True)
        return d

    def get_plugin_dir(self) -> Path:
        return self.root / "plugins"

    def get_base_url(self) -> str:
        return self.site.base_url or ""
