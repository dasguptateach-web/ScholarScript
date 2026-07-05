from datetime import datetime
from typing import List
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from .models import ContentItem, SiteConfig


def generate_sitemap(items: List[ContentItem], base_url: str, output_path: str):
    urlset = Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    pages = [
        ("", "daily", "1.0"),
        ("/archive/index.html", "daily", "0.8"),
        ("/tags/index.html", "daily", "0.7"),
        ("/creative-writing/index.html", "daily", "0.9"),
        ("/author-of-month/index.html", "weekly", "0.6"),
    ]

    for path, freq, priority in pages:
        url = SubElement(urlset, "url")
        loc = SubElement(url, "loc")
        loc.text = f"{base_url}{path}"
        changefreq = SubElement(url, "changefreq")
        changefreq.text = freq
        prio = SubElement(url, "priority")
        prio.text = priority

    for item in items:
        url = SubElement(urlset, "url")
        loc = SubElement(url, "loc")
        loc.text = f"{base_url}/{item.type}/{item.slug}/index.html"
        lastmod = SubElement(url, "lastmod")
        try:
            dt = datetime.strptime(item.date, "%Y-%m-%d")
            lastmod.text = dt.strftime("%Y-%m-%d")
        except Exception:
            lastmod.text = datetime.now().strftime("%Y-%m-%d")
        changefreq = SubElement(url, "changefreq")
        changefreq.text = "monthly"
        prio = SubElement(url, "priority")
        prio.text = "0.7"

    rough = tostring(urlset, encoding="utf-8")
    dom = minidom.parseString(rough)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(dom.toprettyxml(indent="  "))


def generate_rss(items: List[ContentItem], config: SiteConfig, output_path: str):
    rss = Element("rss")
    rss.set("version", "2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    channel = SubElement(rss, "channel")

    title = SubElement(channel, "title")
    title.text = config.title
    link = SubElement(channel, "link")
    link.text = config.base_url
    desc = SubElement(channel, "description")
    desc.text = config.tagline
    lang = SubElement(channel, "language")
    lang.text = config.language

    for item in items[:50]:
        item_el = SubElement(channel, "item")
        i_title = SubElement(item_el, "title")
        i_title.text = item.title
        i_link = SubElement(item_el, "link")
        i_link.text = f"{config.base_url}/{item.type}/{item.slug}/index.html"
        i_guid = SubElement(item_el, "guid")
        i_guid.text = i_link.text
        i_desc = SubElement(item_el, "description")
        i_desc.text = item.summary or ""
        i_pub = SubElement(item_el, "pubDate")
        try:
            dt = datetime.strptime(item.date.split("T")[0], "%Y-%m-%d")
            i_pub.text = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        except Exception:
            i_pub.text = item.date

    rough = tostring(rss, encoding="utf-8")
    dom = minidom.parseString(rough)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(dom.toprettyxml(indent="  "))


def generate_robots(sitemap_url: str, output_path: str):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("User-agent: *\n")
        f.write("Allow: /\n\n")
        f.write(f"Sitemap: {sitemap_url}\n")
