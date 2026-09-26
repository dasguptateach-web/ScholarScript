from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class ContentItem:
    title: str
    slug: str
    type: str  # paper, video, external-link, creative-writing
    date: str
    tags: list = field(default_factory=list)
    author: Optional[str] = None
    author_email: Optional[str] = None
    paypal: Optional[str] = None
    paper_url: Optional[str] = None
    video_url: Optional[str] = None
    external_url: Optional[str] = None
    pen_name: Optional[str] = None
    genre: Optional[str] = None
    cover_image: Optional[str] = None
    summary: Optional[str] = None
    body_html: str = ""
    body_md: str = ""
    word_count: int = 0
    reading_time: int = 1
    og_image: Optional[str] = None
    canonical_url: Optional[str] = None
    hreflang: Optional[str] = None
    ebook_url: Optional[str] = None


@dataclass
class SiteConfig:
    title: str = "ScholarScript"
    tagline: str = "Scripted for Scholars. Powered by Automation."
    domain: str = "scholarscript.org"
    base_url: str = ""
    author: str = "ScholarScript Team"
    language: str = "en"
    locale: str = "en_US"
    theme: str = "classic"
    adsense_client_id: str = ""
    adsense_enabled: bool = True
    goatcounter_code: str = ""
    resend_api_key: str = ""
    owner_email: str = ""
    prize_amount: int = 25
    auto_ingest: bool = True
    ingest_schedule: str = "every 5 minutes"
    submission_auto_mode: bool = True
    plugins_enabled: list = field(default_factory=list)
    affiliate_amazon_tag: str = ""
    affiliate_bookshop_id: str = ""
    social_twitter: str = ""
    social_facebook: str = ""
    social_linkedin: str = ""
    social_youtube: str = ""
    social_bluesky: str = ""
    hreflang_alternates: dict = field(default_factory=dict)


@dataclass
class CloneProfile:
    name: str = "default"
    include_images: bool = True
    include_css: bool = False
    include_js: bool = False
    max_pages: int = 50
    respect_robots: bool = True
    user_agent: str = "ScholarScript/1.0 (Educational Purpose)"
    delay: float = 1.0
    strip_selectors: list = field(default_factory=lambda: ["script", "iframe", ".ad", ".adsense", "#google_ads"])
    exclude_patterns: list = field(default_factory=lambda: ["/wp-admin", "/login", "/signup", "mailto:", "tel:"])
