# ScholarScript

**Scripted for Scholars. Powered by Automation.**

## &#9733; Featured Creative Work

### [The Shadow Cup](https://dasguptateach-web.github.io/ScholarScript/ebooks/the-shadow-cup.html) — by Debojyoti Dasgupta

> A grieving footballer. A girl who draws the future. A tournament for nations that never existed.

A free, fully illustrated 9-chapter story blending magical realism, quantum physics, and football. When Luka Morozov — a retired striker shattered by tragedy — is recruited to play for a nation that doesn't exist on any map, he enters the **Shadow Cup**: a tournament played in a stadium woven from mist and memory, where belief is physics and every goal pulls a thread between worlds.

- [&#9733; Read the Illustrated eBook](https://dasguptateach-web.github.io/ScholarScript/ebooks/the-shadow-cup.html)
- [&#9733; Read on ScholarScript](https://dasguptateach-web.github.io/ScholarScript/creative-writing/the-shadow-cup/)
- [&#9733; eBooks Section](https://dasguptateach-web.github.io/ScholarScript/ebooks/)

---

ScholarScript is a fully autonomous static‑site generator, document ingestion engine, website cloner, and literary community manager — laser‑focused on English Literature scholars (undergraduate, postgraduate, researchers).

## Features

### Content Engine
- All content lives as Markdown (`.md`) files with YAML front matter in `/content/`
- Supported types: **paper**, **video**, **external-link**, **creative-writing**
- Jinja2‑based theming — duplicate `/themes/classic/` to create custom themes
- Watch mode auto‑rebuilds on file changes (`scholarscript watch`)
- Builds complete static site to `/public/` in seconds

### Automatic Content Ingestion
- Drop any document into `/uploads/`: `.doc`, `.docx`, `.pdf`, `.odt`, `.rtf`, `.txt`, `.tex`
- Supports scanned PDFs with OCR fallback (requires Tesseract)
- **`scholarscript ingest`** — processes all pending files automatically:
  1. Extracts text (python‑docx, pdfplumber, Tesseract, odfpy, striprtf)
  2. Derives title from filename or document metadata
  3. Auto‑generates front matter (title, date, tags, type)
  4. Detects content type (paper vs creative‑writing via style analysis)
  5. Extracts DOI / arXiv links from scholarly papers
  6. Converts to clean Markdown and saves to `/content/`
  7. Moves processed files to `/uploads/processed/`
- Configure via `config.yaml`: `auto_ingest`, `ingest_schedule`
- Watch mode for uploads: `scholarscript watch-uploads`

### Website Cloning
```
scholarscript clone https://example.com [--profile academic]
```
- Respectful scraping with configurable delay and `robots.txt` compliance
- Extracts meaningful content, preserves page hierarchy
- Converts HTML → Markdown with auto‑generated front matter
- Downloads images/assets locally
- Strips third‑party scripts, ads, and unwanted elements
- Customisable via JSON profiles in `/clone_profiles/`
- Output ready for build/preview in `/cloned_sites/`

### Creative Writing Submission Pipeline
- Submissions via GitHub Issues using `creative-writing.yml` template
- Template: title, body, author, email, PayPal, pen name, genre, originality
- GitHub Actions workflow triggers on `submission` label:
  - **Auto mode:** creates `.md` directly, closes issue with link
  - **Manual mode:** opens a Pull Request for review
- Mode controlled by `config.yaml: submissions.auto_mode`

### Monthly \$25 Best Contributor Prize
- `scholarscript winner` — determines winner from previous month's pageviews
- Uses GoatCounter free tier for analytics
- Updates `data/author-of-month.json`, rebuilds site with banner + spotlight page
- Sends email notification via Resend (free tier)
- Prize amount configurable in `config.yaml: prize.amount`
- Winner receives \$25 via PayPal (sent manually by owner)

### SEO & Visibility
- Automatic meta tags, Open Graph, Twitter Cards
- Schema.org `Article` and `BreadcrumbList` structured data
- Auto keyword extraction (YAKE‑like) merged with manual tags
- Related Posts widget (shared tags)
- `sitemap.xml`, `rss.xml`, `robots.txt` regenerated on every build
- Social share buttons
- Multilingual `hreflang` support
- Google AdSense auto‑inserted (hidden if `adsense_client_id` is empty)

### Monetisation
- Google AdSense at optimal positions
- Affiliate link transformer for Amazon / Bookshop.org
- Private Financial Health page (no public link) tracking monthly prize payout
- All self‑funding to support the \$25 monthly prize

### Plugin System
- Base class with hooks: `on_build_start`, `on_content_loaded`, `on_page_render`, `on_build_end`
- Drop `.py` files into `/plugins/`, enable via `config.yaml: plugins.enabled`
- Sample plugins included: Reading Time Estimator, LaTeX Renderer (KaTeX CDN)

### CLI Commands
| Command | Description |
|---------|-------------|
| `scholarscript init` | Scaffold folders + sample content |
| `scholarscript ingest` | Process documents in `/uploads/` |
| `scholarscript clone <url>` | Clone a website |
| `scholarscript build` | Generate static site to `/public` |
| `scholarscript preview` | Local dev server (`--port` flag) |
| `scholarscript deploy` | Manual GitHub Pages push |
| `scholarscript winner` | Run monthly prize logic |
| `scholarscript watch` | Auto‑rebuild on content changes |
| `scholarscript watch-uploads` | Auto‑ingest on new uploads |

### Design Principles
- **Never automatically published** — deploy only by explicit `scholarscript deploy` or manual workflow
- **Human‑editable** — all content is plain Markdown + YAML
- **Zero external runtime dependencies** — everything is static HTML at the end
- **GitHub Pages ready** — deploy at zero cost

## Quick Start

```bash
# 1. Install
pip install scholarscript

# 2. Bootstrap a project
scholarscript init my-scholar-site
cd my-scholar-site

# 3. Build and preview
scholarscript build
scholarscript preview

# 4. Add your own content
#    Drop .docx files into uploads/ and run:
scholarscript ingest

# 5. Deploy (manual only!)
scholarscript deploy -m "Initial launch"
```

## Configuration

All settings in `config.yaml`:

```yaml
site:
  title: "ScholarScript"
  tagline: "Scripted for Scholars. Powered by Automation."
  domain: "scholarscript.org"
  base_url: ""
  language: en
  locale: en_US

theme: classic

adsense:
  client_id: ""          # Set to enable AdSense
  enabled: true

goatcounter:
  code: ""               # GoatCounter site code

resend:
  api_key: ""            # Resend API key for prize notifications
  owner_email: ""

prize:
  amount: 25             # Monthly prize amount in USD

ingestion:
  auto_ingest: true      # Auto-process uploads
  schedule: "every 5 minutes"

submissions:
  auto_mode: true        # Auto-create .md from GitHub Issues

plugins:
  enabled: []            # List plugin names to enable

affiliate:
  amazon_tag: ""         # Amazon affiliate tag
  bookshop_id: ""        # Bookshop.org affiliate ID

social:
  twitter: ""
  facebook: ""
  linkedin: ""
  youtube: ""

hreflang: {}             # e.g., { fr: "https://fr.example.com" }
```

## Content Types

### Paper
```yaml
---
title: "Your Paper Title"
date: 2025-06-15
type: paper
author: Dr. Name
tags: [tag1, tag2]
paper_url: "https://doi.org/10.1234/example"
summary: "Brief description..."
---
```

### Video
```yaml
---
title: "Video Title"
date: 2025-06-15
type: video
author: Name
tags: [tag1, tag2]
video_url: "https://youtube.com/watch?v=..."
summary: "Brief description..."
---
```

### Creative Writing
```yaml
---
title: "My Poem"
date: 2025-06-15
type: creative-writing
author: "Real Name"
pen_name: "Pen Name"
tags: [poetry, nature]
genre: Poetry
paypal: "author@example.com"
summary: "Brief description..."
---
```

### External Link
```yaml
---
title: "Resource Name"
date: 2025-06-15
type: external-link
tags: [resources]
external_url: "https://example.com"
summary: "Brief description..."
---
```

## Content Ingestion Details

### Supported Formats
| Format | Library | OCR Fallback |
|--------|---------|-------------|
| `.docx` | python‑docx | — |
| `.pdf` | pdfplumber / PyPDF2 | Tesseract (scanned PDFs) |
| `.odt` | odfpy | — |
| `.rtf` | striprtf | — |
| `.txt` | built‑in | — |
| `.tex` | regex extraction | — |
| `.doc` | antiword / catdoc | — |

### What Happens During Ingestion
1. File detected in `/uploads/`
2. Text extracted using appropriate library
3. Title cleaned from filename or document metadata
4. Date from file mtime or document metadata
5. Tags extracted via keyword frequency analysis
6. Content type auto‑detected (prose vs poetry analysis)
7. DOI / arXiv links extracted from header/footer
8. Text converted to clean Markdown
9. `.md` saved to `/content/papers/` or `/content/creative-writing/`
10. Original moved to `/uploads/processed/`

## Website Cloning

### Profiles
Clone behaviour is customised by JSON profiles in `/clone_profiles/`:

```bash
scholarscript clone https://example.com --profile academic
```

**`clone_profiles/academic.json`:**
```json
{
  "include_images": true,
  "include_css": false,
  "include_js": false,
  "max_pages": 20,
  "respect_robots": true,
  "delay": 2.0,
  "strip_selectors": ["script", "iframe", ".ad", ".nav", ".sidebar"],
  "exclude_patterns": ["/wp-admin", "/login", "/pdf"]
}
```

### Profile Fields
| Field | Default | Description |
|-------|---------|-------------|
| `include_images` | `true` | Download local copies of images |
| `include_css` | `false` | Include CSS in output |
| `include_js` | `false` | Include JavaScript in output |
| `max_pages` | `50` | Maximum pages to crawl |
| `respect_robots` | `true` | Obey `robots.txt` directives |
| `delay` | `1.0` | Seconds between requests |
| `strip_selectors` | `[script, iframe, .ad]` | CSS selectors to remove |
| `exclude_patterns` | `[/wp-admin, /login]` | URL patterns to skip |

## Themes

All design lives in `/themes/` as Jinja2 templates:

```
themes/
  classic/
    base.html           # Main layout
    index.html          # Homepage
    archive.html        # Content listing pages
    content.html        # Individual item page
    tags.html           # Tag cloud
    author-of-month.html
    donate.html
    health.html         # Private financial page
    css/style.css
    js/
    img/
```

To create a custom theme:
```bash
cp -r themes/classic themes/my-theme
# Edit templates and CSS
# Set config.yaml: theme: my-theme
```

## Plugins

Drop Python files into `/plugins/`. Each plugin extends the base class:

```python
from scholarscript.plugins import ScholarScriptPlugin

class MyPlugin(ScholarScriptPlugin):
    name = "my-plugin"
    version = "1.0.0"

    def on_build_start(self, config, items):
        pass
    def on_content_loaded(self, items):
        pass
    def on_page_render(self, template_name, context):
        return context
    def on_build_end(self, public_dir):
        pass
```

Enable in `config.yaml`:
```yaml
plugins:
  enabled: [reading_time, latex_renderer]
```

### Included Sample Plugins
- **Reading Time Estimator** — Calculates reading time and generates summaries
- **LaTeX Renderer** — Injects KaTeX CDN when LaTeX is detected

## Deployment

### Never Automatic
ScholarScript never publishes without explicit permission. The site goes live only by:

1. **Manual CLI:** `scholarscript deploy`
2. **Manual GitHub Action:** Trigger `Deploy to GitHub Pages` from the Actions tab

### GitHub Pages Setup
1. Create a GitHub repository
2. Push your ScholarScript project
3. Go to Settings → Pages → Source: GitHub Actions
4. Run `scholarscript deploy` or trigger the Action manually

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/yourname/yourrepo.git
git push -u origin main

# Then deploy
scholarscript deploy -m "First deployment"
```

## Prize System

The monthly $25 "Best Contributor" prize works as follows:

1. Pageviews are tracked via GoatCounter (free tier)
2. At month's end, run `scholarscript winner`
3. The creative‑writing author with the highest aggregate pageviews wins
4. `data/author-of-month.json` is updated
5. Site is rebuilt with homepage banner and spotlight page
6. Owner receives email notification with winner's PayPal
7. Owner manually sends the prize

To modify the prize amount, edit `config.yaml`:
```yaml
prize:
  amount: 50   # Change to any amount
```

## Realistic Monetisation Expectations

| Source | Estimated Monthly | Notes |
|--------|-------------------|-------|
| AdSense | $1–$10 | Requires ~1,000 monthly visits |
| Amazon Affiliates | $0–$5 | Book links only |
| Bookshop Affiliates | $0–$5 | Higher margins |
| **Total** | **$1–$20** | Enough to self‑fund the $25 prize with some personal contribution |

## Project Structure

```
scholarscript/
├── scholarscript/           # Python package
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # CLI commands
│   ├── config.py           # Configuration loader
│   ├── engine.py           # Core SSG engine
│   ├── parser.py           # Markdown/YAML parser
│   ├── ingestion.py        # Document ingestion
│   ├── cloner.py           # Website cloner
│   ├── seo.py              # Sitemap, RSS, robots
│   ├── analytics.py        # GoatCounter integration
│   ├── plugins.py          # Plugin system
│   └── templates/          # Built‑in template fallbacks
├── content/                 # Content (Markdown + YAML)
│   ├── papers/
│   ├── videos/
│   ├── creative-writing/
│   └── external-links/
├── themes/                  # Jinja2 templates
│   └── classic/
│       ├── base.html
│       ├── index.html
│       ├── archive.html
│       ├── content.html
│       ├── tags.html
│       ├── author-of-month.html
│       ├── donate.html
│       ├── health.html
│       ├── css/style.css
│       └── js/
├── uploads/                 # Drop documents here
│   └── processed/           # Processed files moved here
├── plugins/                 # User‑created plugins
├── clone_profiles/          # Cloning configuration
├── cloned_sites/            # Cloned website output
├── data/                    # Site data (author‑of‑month)
├── public/                  # Generated static site
├── .github/                 # GitHub templates & workflows
│   ├── ISSUE_TEMPLATE/
│   │   └── creative-writing.yml
│   └── workflows/
│       ├── deploy.yml
│       └── process-submission.yml
├── config.yaml              # All site configuration
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Building from Source

```bash
git clone https://github.com/scholarscript/scholarscript.git
cd scholarscript
pip install -e ".[all]"
scholarscript --help
```

### Build Single‑File Executable

```bash
pip install pyinstaller
pyinstaller --onefile --name scholarscript scholarscript/__main__.py
dist/scholarscript --help
```

## Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt`

## License

MIT
