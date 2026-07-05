import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import click

from . import VERSION
from .config import Config, find_project_root, DEFAULT_CONFIG
from .engine import Engine
from .ingestion import IngestionEngine
from .cloner import WebsiteCloner
from .models import CloneProfile


def _get_config(ctx, param, value) -> Config:
    return Config()


@click.group()
@click.version_option(version=VERSION, prog_name="scholarscript")
def cli():
    """ScholarScript - Scripted for Scholars. Powered by Automation."""
    pass


@cli.command()
@click.argument("path", default=".", type=click.Path())
def init(path):
    """Bootstrap a new ScholarScript project."""
    root = Path(path).resolve()
    if (root / "config.yaml").exists():
        click.echo("Project already initialized.")
        return

    click.echo(f"Initializing ScholarScript at {root}...")

    # Create directory structure
    dirs = [
        "content/papers", "content/videos", "content/creative-writing",
        "content/external-links", "themes/classic/css", "themes/classic/js",
        "themes/classic/img", "data", "plugins", "clone_profiles",
        "uploads/processed", "public", "cloned_sites",
        ".github/ISSUE_TEMPLATE", ".github/workflows",
    ]
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)

    # Write config.yaml
    import yaml
    with open(root / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)

    click.echo("  Writing sample content...")
    _write_sample_content(root)

    click.echo("  Installing templates...")
    _write_templates(root)

    click.echo("  Writing sample plugins...")
    _write_sample_plugins(root)

    click.echo("  Writing clone profile...")
    _write_clone_profiles(root)

    click.echo("  Writing GitHub templates...")
    _write_github_templates(root)

    click.echo("")
    click.echo("ScholarScript project initialized!")
    click.echo("")
    click.echo("  Next steps:")
    click.echo("    cd " + str(root))
    click.echo("    pip install -r requirements.txt")
    click.echo("    scholarscript build")
    click.echo("    scholarscript preview")
    click.echo("")
    click.echo("  To ingest documents:")
    click.echo("    Drop .docx/.pdf/.txt files into uploads/")
    click.echo("    scholarscript ingest")
    click.echo("")
    click.echo("  To clone a website:")
    click.echo("    scholarscript clone https://example.com")


@cli.command()
@click.pass_context
def build(ctx):
    """Build the static site into /public."""
    cfg = _get_config(ctx, None, None)
    click.echo("Building site...")
    engine = Engine(cfg)
    start = time.time()
    engine.build()
    elapsed = time.time() - start
    click.echo(f"Built {len(engine.items)} items in {elapsed:.2f}s")
    click.echo(f"Output: {cfg.get_public_dir()}")


@cli.command()
@click.option("--port", default=8000, help="Port for preview server")
@click.pass_context
def preview(ctx, port):
    """Start a local preview server."""
    cfg = _get_config(ctx, None, None)
    public_dir = cfg.get_public_dir()

    if not public_dir.exists() or not list(public_dir.iterdir()):
        click.echo("No built site found. Running build first...")
        ctx.invoke(build)

    click.echo(f"Serving at http://localhost:{port}")
    click.echo("Press Ctrl+C to stop.")

    os.chdir(str(public_dir))
    try:
        subprocess.run([sys.executable, "-m", "http.server", str(port)])
    except KeyboardInterrupt:
        pass


@cli.command()
@click.option("--message", "-m", default="ScholarScript auto-deploy", help="Commit message")
@click.pass_context
def deploy(ctx, message):
    """Deploy to GitHub Pages via API."""
    cfg = _get_config(ctx, None, None)
    click.echo("Deploying to GitHub Pages...")
    from .deployer import deploy_to_github_pages
    success = deploy_to_github_pages(cfg)
    if success:
        click.echo("Deployment complete!")
    else:
        click.echo("Deployment failed or cancelled.")

    click.echo("Deployment initiated (check GitHub Actions for completion).")


@cli.command()
@click.pass_context
def ingest(ctx):
    """Manually trigger ingestion of documents in /uploads."""
    cfg = _get_config(ctx, None, None)
    engine = IngestionEngine(cfg.get_uploads_dir(), cfg.get_content_dir())

    click.echo("Checking uploads folder...")
    results = engine.ingest_all()

    success = [r for r in results if r["status"] == "success"]
    errors = [r for r in results if r["status"] == "error"]

    click.echo(f"Processed {len(results)} file(s):")
    click.echo(f"  Success: {len(success)}")
    click.echo(f"  Errors:  {len(errors)}")

    for r in success:
        click.echo(f"  [OK] {r['file']} -> {r['output']} ({r['type']})")
    for r in errors:
        click.echo(f"  [ERR] {r['file']}: {r['error']}")

    if success:
        click.echo("")
        click.echo("Run 'scholarscript build' to rebuild the site.")


@cli.command()
@click.argument("url")
@click.option("--profile", default="default", help="Clone profile name")
@click.pass_context
def clone(ctx, url, profile):
    """Clone a website into Markdown content."""
    cfg = _get_config(ctx, None, None)

    prof = cfg.clone_profiles.get(profile, CloneProfile())
    cloner = WebsiteCloner(prof)

    click.echo(f"Cloning {url}...")
    try:
        result = cloner.clone(url, cfg.get_cloned_dir())
        click.echo(f"Cloned {result['pages']} pages to {result['output']}")
        click.echo("")
        click.echo("To copy content into your site:")
        click.echo(f"  Copy files from {result['output']}/ to content/")
        click.echo("  Then run: scholarscript build")
    except Exception as e:
        click.echo(f"Error cloning: {e}", err=True)


@cli.command()
@click.pass_context
def winner(ctx):
    """Determine and announce the monthly prize winner."""
    cfg = _make_config()
    data_dir = cfg.get_data_dir()
    aom_path = data_dir / "author-of-month.json"

    from .analytics import get_top_author_pages
    month = (datetime.now() - timedelta(days=1)).strftime("%Y-%m")
    views = get_top_author_pages(cfg.site, data_dir, month)

    if not views:
        click.echo("No pageview data available for the previous month.")
        return

    winner = max(views, key=views.get)
    winner_data = {
        "month": month,
        "author": winner,
        "views": views[winner],
        "prize": cfg.site.prize_amount,
        "announced": datetime.now().isoformat(),
    }

    with open(aom_path, "w", encoding="utf-8") as f:
        json.dump(winner_data, f, indent=2)

    click.echo(f"Winner: {winner} with {views[winner]} views")
    click.echo(f"Prize: ${cfg.site.prize_amount}")

    # Send email notification
    _send_winner_email(cfg, winner_data)

    click.echo("Author of month updated. Run 'scholarscript build' to update site.")


@cli.command()
@click.option("--rebuild/--no-rebuild", default=True)
@click.pass_context
def watch(ctx, rebuild):
    """Watch content directory for changes and auto-rebuild."""
    cfg = _make_config()
    content_dir = cfg.get_content_dir()

    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        click.echo("Install watchdog: pip install watchdog")
        return

    class RebuildHandler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.src_path.endswith(".md"):
                click.echo(f"Change detected: {event.src_path}")
                if rebuild:
                    ctx.invoke(build)

    observer = Observer()
    handler = RebuildHandler()
    observer.schedule(handler, str(content_dir), recursive=True)
    observer.start()

    click.echo(f"Watching {content_dir} for changes...")
    click.echo("Press Ctrl+C to stop.")

    if rebuild:
        ctx.invoke(build)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


@cli.command()
@click.pass_context
def watch_uploads(ctx):
    """Watch the uploads folder for new files and auto-ingest."""
    cfg = _make_config()
    uploads_dir = cfg.get_uploads_dir()

    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        click.echo("Install watchdog: pip install watchdog")
        return

    class IngestionHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            click.echo(f"New file detected: {event.src_path}")
            ctx.invoke(ingest)
            ctx.invoke(build)

    observer = Observer()
    handler = IngestionHandler()
    observer.schedule(handler, str(uploads_dir), recursive=False)
    observer.start()

    click.echo(f"Watching {uploads_dir} for new uploads...")
    click.echo("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def _make_config():
    return Config()


def _write_sample_content(root: Path):
    """Write sample content files for the demo site."""
    content = root / "content"

    # Paper 1
    (content / "papers" / "shakespeare-tempest.md").write_text(
        '---\n'
        'title: "Colonial Discourse in The Tempest"\n'
        'date: 2025-06-15\n'
        'type: paper\n'
        'author: Dr. Eleanor Chase\n'
        'tags: [shakespeare, postcolonial, renaissance, tempest]\n'
        'paper_url: "https://doi.org/10.1234/example"\n'
        'summary: "An analysis of colonial power structures in Shakespeare\\\'s The Tempest, examining Caliban as a representation of the colonised subject."\n'
        '---\n\n'
        '# Colonial Discourse in *The Tempest*\n\n'
        '## Introduction\n\n'
        'Shakespeare\'s *The Tempest* has long been a focal point for postcolonial literary criticism. '
        'The play, written circa 1610–1611, presents a microcosm of colonial encounter through the '
        'relationship between Prospero, the European magus, and Caliban, the indigene of the island.\n\n'
        '## Caliban as the Colonised Subject\n\n'
        'Stephen Greenblatt argues that Caliban represents the "other" upon which colonial identity is constructed. '
        'His language—taught by Prospero and then used to curse him—embodies the paradox of colonial education.\n\n'
        '## The Language of Power\n\n'
        'When Caliban declares, "You taught me language, and my profit on\'t / Is, I know how to curse" (I.ii.362–363), '
        'he articulates the double-edged nature of colonial pedagogy. Language becomes both a tool of oppression and '
        'a weapon of resistance.\n\n'
        '## Conclusion\n\n'
        '*The Tempest* remains remarkably relevant for contemporary discussions of colonialism, power, and resistance. '
        'Prospero\'s island is a stage upon which the dynamics of empire are played out in miniature.'
    )

    # Paper 2
    (content / "papers" / "victorian-poetry.md").write_text(
        '---\n'
        'title: "The City in Victorian Poetry"\n'
        'date: 2025-06-10\n'
        'type: paper\n'
        'author: Dr. Mark Rivera\n'
        'tags: [victorian, poetry, urban, industrial, tennyson, arnold]\n'
        'summary: "Exploring representations of the Victorian city in the poetry of Tennyson, Arnold, and Browning."\n'
        '---\n\n'
        '# The City in Victorian Poetry\n\n'
        '## Introduction\n\n'
        'The Victorian city was a space of contradiction—both a symbol of progress and a site of profound alienation. '
        'This paper examines how three major Victorian poets grappled with urban modernity.\n\n'
        '## Tennyson\'s London\n\n'
        'Alfred, Lord Tennyson\'s poetry often reflects the tension between pastoral nostalgia and urban reality. '
        'In "Locksley Hall," the speaker looks toward the future with a mixture of hope and dread.\n\n'
        '## Matthew Arnold\'s "Darkling Plain"\n\n'
        'Arnold\'s "Dover Beach" presents the most famous Victorian image of retreating faith, using the sea '
        'as a metaphor for a receding spiritual certainty in an increasingly mechanised world.\n\n'
        '## Browning\'s Dramatic Monologues\n\n'
        'Robert Browning\'s dramatic monologues give voice to the urban experience through the lens of individual '
        'psychology, revealing the inner lives of city dwellers.'
    )

    # Paper 3
    (content / "papers" / "postmodern-narrative.md").write_text(
        '---\n'
        'title: "Fractured Selves: Narrative Identity in Postmodern Fiction"\n'
        'date: 2025-06-05\n'
        'type: paper\n'
        'author: Prof. Sarah Chen\n'
        'tags: [postmodern, narrative, identity, theory, pynchon, delillo]\n'
        'summary: "An examination of how postmodern narrative techniques reflect contemporary theories of fragmented identity."\n'
        '---\n\n'
        '# Fractured Selves: Narrative Identity in Postmodern Fiction\n\n'
        '## Introduction\n\n'
        'Postmodern fiction challenges the notion of a unified, coherent self. Through fragmentation, '
        'metafiction, and narrative instability, writers like Thomas Pynchon and Don DeLillo explore '
        'identity as a construct rather than an essence.\n\n'
        '## Pynchon and Paranoia as Structure\n\n'
        'In *The Crying of Lot 49*, Thomas Pynchon uses the conspiracy plot as a structural analogue '
        'for the fragmented postmodern subject. Oedipa Maas\'s journey through the labyrinthine systems '
        'of meaning reflects the impossibility of a stable identity.\n\n'
        '## DeLillo and the Mediated Self\n\n'
        'Don DeLillo\'s *White Noise* examines how media saturation creates a fractured sense of self. '
        'The characters define themselves through brand names, television images, and academic jargon.\n\n'
        '## Conclusion\n\n'
        'Postmodern narrative techniques do more than experiment with form; they enact the very '
        'fragmentation they describe, making the reader experience the instability of identity.'
    )

    # Video 1
    (content / "videos" / "literary-theory-intro.md").write_text(
        '---\n'
        'title: "Introduction to Literary Theory: A Visual Guide"\n'
        'date: 2025-06-12\n'
        'type: video\n'
        'author: ScholarScript Team\n'
        'tags: [literary-theory, introduction, criticism, guide]\n'
        'video_url: "https://www.youtube.com/watch?v=example1"\n'
        'summary: "A comprehensive visual introduction to the major schools of literary theory."\n'
        '---\n\n'
        '# Introduction to Literary Theory: A Visual Guide\n\n'
        'This video covers the major schools of literary theory:\n\n'
        '- **Formalism** – Close reading and textual analysis\n'
        '- **Structuralism** – Underlying systems of meaning\n'
        '- **Poststructuralism** – Deconstruction and instability\n'
        '- **Psychoanalytic Criticism** – The unconscious in texts\n'
        '- **Feminist Criticism** – Gender and power\n'
        '- **Postcolonial Criticism** – Empire and its aftermath\n\n'
        'Ideal for undergraduates beginning their journey into literary theory.'
    )

    # Video 2
    (content / "videos" / "hamlet-analysis.md").write_text(
        '---\n'
        'title: "Hamlet\\\'s Soliloquies: A Line-by-Line Analysis"\n'
        'date: 2025-06-08\n'
        'type: video\n'
        'author: Dr. Eleanor Chase\n'
        'tags: [shakespeare, hamlet, soliloquy, analysis, elizabethan]\n'
        'video_url: "https://www.youtube.com/watch?v=example2"\n'
        'summary: "A detailed analysis of Hamlet\\\'s seven soliloquies, examining rhetorical structure and thematic development."\n'
        '---\n\n'
        "# Hamlet's Soliloquies: A Line-by-Line Analysis\n\n"
        'A detailed breakdown of all seven of Hamlet\'s soliloquies, examining:\n\n'
        '1. "O, that this too, too solid flesh would melt" (I.ii)\n'
        '2. "O, what a rogue and peasant slave am I!" (II.ii)\n'
        '3. "To be, or not to be" (III.i)\n'
        '4. "Speak the speech, I pray you" (III.ii)\n'
        '5. "Tis now the very witching time of night" (III.ii)\n'
        '6. "Now might I do it pat" (III.iii)\n'
        '7. "How all occasions do inform against me" (IV.iv)\n\n'
        'Each soliloquy is analysed for its rhetorical structure, thematic content, and dramatic function.'
    )

    # Creative Writing 1
    (content / "creative-writing" / "autumn-whispers.md").write_text(
        '---\n'
        'title: "Autumn Whispers"\n'
        'date: 2025-06-14\n'
        'type: creative-writing\n'
        'author: "Eleanor Chase"\n'
        'pen_name: "The Quiet Quill"\n'
        'tags: [poetry, autumn, nature, reflection]\n'
        'genre: Poetry\n'
        'paypal: "eleanor@example.com"\n'
        'summary: "A poem about the quiet transformation of autumn."\n'
        '---\n\n'
        "# Autumn Whispers\n\n"
        'Leaves descend in amber light,\n'
        'Silent dancers taking flight.\n'
        'Crisp the air, the earth releases\n'
        'Summer\'s ghost in golden fleeces.\n\n'
        'Footsteps echo on the lane,\n'
        'Mist dissolves in morning rain.\n'
        'Every breath a fragile glass\n'
        'Shatters as the moments pass.\n\n'
        'Trees undress with quiet grace,\n'
        'Baring branches, time and space\n'
        'Etched in rings of what has been—\n'
        'Winter waits behind the green.'
    )

    # Creative Writing 2
    (content / "creative-writing" / "digital-nostalgia.md").write_text(
        '---\n'
        'title: "Digital Nostalgia"\n'
        'date: 2025-06-11\n'
        'type: creative-writing\n'
        'author: "Mark Rivera"\n'
        'pen_name: "River of Words"\n'
        'tags: [prose, technology, memory, modern-life]\n'
        'genre: Creative Non-Fiction\n'
        'paypal: "mark@example.com"\n'
        'summary: "A reflection on growing up in the gap between analogue and digital worlds."\n'
        '---\n\n'
        "# Digital Nostalgia\n\n"
        'I remember the sound of a dial-up modem. That screeching, staticky handshake '
        'between two machines—a sound that meant connection, possibility, the world '
        'entering our living room through a telephone line.\n\n'
        'My children will never know that sound. They will never feel the particular '
        'anxiety of waiting for a webpage to load, line by line, on a monochrome monitor. '
        'They swipe. They tap. They expect immediacy.\n\n'
        'But I wonder: what is lost when there is no waiting? What happens to desire '
        'when everything is instantly available?'
    )

    # Creative Writing 3
    (content / "creative-writing" / "urban-echoes.md").write_text(
        '---\n'
        'title: "Urban Echoes"\n'
        'date: 2025-06-02\n'
        'type: creative-writing\n'
        'author: "Sarah Chen"\n'
        'pen_name: "Scribe of the City"\n'
        'tags: [poetry, urban, city-life, night]\n'
        'genre: Poetry\n'
        'paypal: "sarah@example.com"\n'
        'summary: "Poems from the city at night."\n'
        '---\n\n'
        "# Urban Echoes\n\n"
        'Neon drips on rain-slicked street,\n'
        'Midnight finds the city\'s fleet\n'
        'Of solitary souls who wander\n'
        'Through the shadows, thinking yonder\n'
        'Thoughts that only darkness breeds\n'
        'Planting unexpected seeds.\n\n'
        'Subway rumble, distant siren,\n'
        'Every city-dweller\'s horizon\n'
        'Tipped with light and edged with grey—\n'
        'Night dissolves into the day\n'
        'Through a haze of coffee steam,\n'
        'Waking from a concrete dream.'
    )

    # External Link 1
    (content / "external-links" / "modernism-resource.md").write_text(
        '---\n'
        'title: "The Modernist Studies Research Network"\n'
        'date: 2025-06-01\n'
        'type: external-link\n'
        'tags: [modernism, research, resources, network]\n'
        'external_url: "https://www.moderniststudies.org"\n'
        'summary: "A comprehensive research network for scholars of literary modernism."\n'
        '---\n\n'
        '# The Modernist Studies Research Network\n\n'
        'A comprehensive research network for scholars of literary modernism. '
        'Features include conference listings, publication opportunities, and a '
        'curated bibliography of recent scholarship.\n\n'
        '[Visit the Modernist Studies Research Network](https://www.moderniststudies.org)'
    )

    # Author of month data
    aom = {
        "month": "2025-05",
        "author": "The Quiet Quill",
        "views": 342,
        "prize": 25,
        "announced": "2025-06-01T00:00:00",
    }
    with open(root / "data" / "author-of-month.json", "w") as f:
        json.dump(aom, f, indent=2)


def _write_templates(root: Path):
    """Write default theme templates."""
    theme_dir = root / "themes" / "classic"

    # base.html
    (theme_dir / "base.html").write_text(
        '<!DOCTYPE html>\n'
        '<html lang="{{ site.language }}">\n'
        '<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '  <title>{{ page_title }} - {{ site.title }}</title>\n'
        '  <meta name="description" content="{{ page_description | default(site.tagline) }}">\n'
        '  <meta name="generator" content="ScholarScript">\n'
        '  <link rel="stylesheet" href="{{ base_url }}/css/style.css">\n'
        '  <link rel="alternate" type="application/rss+xml" title="{{ site.title }}" href="{{ base_url }}/rss.xml">\n'
        '{% if site.adsense_client_id and site.adsense_enabled %}\n'
        '  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={{ site.adsense_client_id }}" crossorigin="anonymous"></script>\n'
        '{% endif %}\n'
        '{% if site.goatcounter_code %}\n'
        '  <script data-goatcounter="https://{{ site.goatcounter_code }}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>\n'
        '{% endif %}\n'
        '</head>\n'
        '<body>\n'
        '  <header class="site-header">\n'
        '    <div class="container">\n'
        '      <a href="{{ base_url }}/" class="logo">\n'
        '        <h1>{{ site.title }}</h1>\n'
        '        <p class="tagline">{{ site.tagline }}</p>\n'
        '      </a>\n'
        '      <nav class="main-nav">\n'
        '        <a href="{{ base_url }}/">Home</a>\n'
        '        <a href="{{ base_url }}/papers/">Papers</a>\n'
        '        <a href="{{ base_url }}/videos/">Videos</a>\n'
        '        <a href="{{ base_url }}/creative-writing/">Creative Writing</a>\n'
        '        <a href="{{ base_url }}/external-links/">External Links</a>\n'
        '        <a href="{{ base_url }}/tags/">Tags</a>\n'
        '        <a href="{{ base_url }}/author-of-month/">Author of the Month</a>\n'
        '        <a href="{{ base_url }}/donate/">Support Us</a>\n'
        '      </nav>\n'
        '    </div>\n'
        '  </header>\n\n'
        '  <main class="container">\n'
        '    {% block content %}{% endblock %}\n'
        '  </main>\n\n'
        '  <footer class="site-footer">\n'
        '    <div class="container">\n'
        '      <p>&copy; {{ now.year }} {{ site.title }}. Powered by ScholarScript.</p>\n'
        '{% if site.social_twitter or site.social_facebook or site.social_linkedin %}\n'
        '      <div class="social-links">\n'
        '{% if site.social_twitter %}        <a href="https://twitter.com/{{ site.social_twitter }}" target="_blank" rel="noopener">Twitter</a>{% endif %}\n'
        '{% if site.social_facebook %}        <a href="https://facebook.com/{{ site.social_facebook }}" target="_blank" rel="noopener">Facebook</a>{% endif %}\n'
        '{% if site.social_linkedin %}        <a href="https://linkedin.com/in/{{ site.social_linkedin }}" target="_blank" rel="noopener">LinkedIn</a>{% endif %}\n'
        '      </div>\n'
        '{% endif %}\n'
        '    </div>\n'
        '  </footer>\n'
        '</body>\n'
        '</html>'
    )

    # index.html
    (theme_dir / "index.html").write_text(
        '{% extends "base.html" %}\n'
        '{% block content %}\n'
        '<section class="hero">\n'
        '  <h2>Welcome to {{ site.title }}</h2>\n'
        '  <p>{{ site.tagline }}</p>\n'
        '</section>\n\n'
        '{% if author_of_month %}\n'
        '<section class="author-spotlight">\n'
        '  <h3>Author of the Month</h3>\n'
        '  <p>Congratulations to <strong>{{ author_of_month.author }}</strong> with {{ author_of_month.views }} views!</p>\n'
        '  <a href="{{ base_url }}/author-of-month/" class="btn">Learn More</a>\n'
        '</section>\n'
        '{% endif %}\n\n'
        '{% if papers %}\n'
        '<section class="recent-papers">\n'
        '  <h3>Latest Papers</h3>\n'
        '  {% for item in papers %}\n'
        '  <article class="card">\n'
        '    <h4><a href="{{ base_url }}/paper/{{ item.slug }}/">{{ item.title }}</a></h4>\n'
        '    <p class="meta">{{ item.date }} &middot; {{ item.author }}</p>\n'
        '    <p>{{ item.summary }}</p>\n'
        '    <div class="tags">{% for tag in item.tags %}<span class="tag">{{ tag }}</span> {% endfor %}</div>\n'
        '  </article>\n'
        '  {% endfor %}\n'
        '</section>\n'
        '{% endif %}\n\n'
        '{% if creative %}\n'
        '<section class="recent-creative">\n'
        '  <h3>Latest Creative Writing</h3>\n'
        '  {% for item in creative %}\n'
        '  <article class="card">\n'
        '    <h4><a href="{{ base_url }}/creative-writing/{{ item.slug }}/">{{ item.title }}</a></h4>\n'
        '    <p class="meta">{{ item.date }} &middot; {{ item.pen_name or item.author }}</p>\n'
        '    <p>{{ item.summary }}</p>\n'
        '  </article>\n'
        '  {% endfor %}\n'
        '</section>\n'
        '{% endif %}\n'
        '{% endblock %}'
    )

    # archive.html
    (theme_dir / "archive.html").write_text(
        '{% extends "base.html" %}\n'
        '{% block content %}\n'
        '<h2>{{ page_title }}</h2>\n'
        '{% if items %}\n'
        '  {% for item in items %}\n'
        '  <article class="card">\n'
        '    <h3><a href="{{ base_url }}/{{ item.type }}/{{ item.slug }}/">{{ item.title }}</a></h3>\n'
        '    <p class="meta">{{ item.date }}{% if item.author %} &middot; {{ item.author }}{% endif %}</p>\n'
        '    <p>{{ item.summary }}</p>\n'
        '    <div class="tags">{% for tag in item.tags %}<span class="tag">{{ tag }}</span> {% endfor %}</div>\n'
        '  </article>\n'
        '  {% endfor %}\n'
        '{% else %}\n'
        '  <p>No content yet.</p>\n'
        '{% endif %}\n'
        '{% endblock %}'
    )

    # content.html
    (theme_dir / "content.html").write_text(
        '{% extends "base.html" %}\n'
        '{% block content %}\n'
        '<article class="content-page">\n'
        '  <h2>{{ item.title }}</h2>\n'
        '  <p class="meta">\n'
        '    {{ item.date }}\n'
        '{% if item.author %} &middot; {{ item.author }}{% endif %}\n'
        '{% if item.pen_name %} &middot; {{ item.pen_name }}{% endif %}\n'
        '    &middot; {{ item.reading_time }} min read\n'
        '  </p>\n\n'
        '{% if item.summary %}\n'
        '  <blockquote class="summary">{{ item.summary }}</blockquote>\n'
        '{% endif %}\n\n'
        '  <div class="content-body">\n'
        '    {{ item.body_html | safe }}\n'
        '  </div>\n\n'
        '  <div class="tags">{% for tag in item.tags %}<span class="tag">{{ tag }}</span> {% endfor %}</div>\n\n'
        '{% if item.paper_url %}\n'
        '  <p><a href="{{ item.paper_url }}" target="_blank" rel="noopener">View Original Paper</a></p>\n'
        '{% endif %}\n'
        '{% if item.video_url %}\n'
        '  <div class="video-embed"><a href="{{ item.video_url }}" target="_blank" rel="noopener">Watch Video</a></div>\n'
        '{% endif %}\n'
        '{% if item.external_url %}\n'
        '  <p><a href="{{ item.external_url }}" target="_blank" rel="noopener">Visit External Link</a></p>\n'
        '{% endif %}\n\n'
        '{% if related %}\n'
        '  <section class="related">\n'
        '    <h3>Related Posts</h3>\n'
        '    <ul>\n'
        '    {% for r in related %}\n'
        '      <li><a href="{{ base_url }}/{{ r.type }}/{{ r.slug }}/">{{ r.title }}</a></li>\n'
        '    {% endfor %}\n'
        '    </ul>\n'
        '  </section>\n'
        '{% endif %}\n'
        '</article>\n'
        '{% endblock %}'
    )

    # tags.html
    (theme_dir / "tags.html").write_text(
        '{% extends "base.html" %}\n'
        '{% block content %}\n'
        '<h2>Tags</h2>\n'
        '<div class="tag-cloud">\n'
        '{% for tag, items in tags.items() %}\n'
        '  <span class="tag" style="font-size: {{ [0.8 + (items|length * 0.1), 2.0] | min }}em">\n'
        '    <a href="#{{ tag }}">{{ tag }} ({{ items|length }})</a>\n'
        '  </span>\n'
        '{% endfor %}\n'
        '</div>\n\n'
        '{% for tag, items in tags.items() %}\n'
        '<section id="{{ tag }}">\n'
        '  <h3>{{ tag }}</h3>\n'
        '  <ul>\n'
        '  {% for item in items %}\n'
        '    <li><a href="{{ base_url }}/{{ item.type }}/{{ item.slug }}/">{{ item.title }}</a> <span class="meta">{{ item.date }}</span></li>\n'
        '  {% endfor %}\n'
        '  </ul>\n'
        '</section>\n'
        '{% endfor %}\n'
        '{% endblock %}'
    )

    # author-of-month.html
    (theme_dir / "author-of-month.html").write_text(
        '{% extends "base.html" %}\n'
        '{% block content %}\n'
        '<h2>Author of the Month</h2>\n'
        '{% if author %}\n'
        '<div class="aom-card">\n'
        '  <h3>{{ author.author }}</h3>\n'
        '  <p class="meta">{{ author.month }} &middot; {{ author.views }} pageviews</p>\n'
        '  <p>Prize: ${{ author.prize }}</p>\n'
        '  <p>Congratulations to our winner! The ${{ author.prize }} prize will be sent via PayPal.</p>\n'
        '</div>\n'
        '{% else %}\n'
        '  <p>No winner announced yet. Check back next month!</p>\n'
        '{% endif %}\n'
        '{% endblock %}'
    )

    # donate.html
    (theme_dir / "donate.html").write_text(
        '{% extends "base.html" %}\n'
        '{% block content %}\n'
        '<h2>Support ScholarScript</h2>\n'
        '<p>ScholarScript is a free, open-source platform for English Literature scholars. '
        'Your support helps us maintain the site and fund our monthly $25 Best Contributor prize.</p>\n\n'
        '<h3>How You Can Help</h3>\n'
        '<ul>\n'
        '  <li><strong>Submit your work</strong> – Share your papers, videos, and creative writing</li>\n'
        '  <li><strong>Tell your colleagues</strong> – Word of mouth is our best advertising</li>\n'
        '  <li><strong>Support our sponsors</strong> – Use our affiliate links when shopping for books</li>\n'
        '</ul>\n\n'
        '<h3>Affiliate Book Shopping</h3>\n'
        '{% if site.affiliate_amazon_tag %}\n'
        '<p><a href="https://www.amazon.com/?tag={{ site.affiliate_amazon_tag }}" target="_blank" rel="nofollow">Shop on Amazon</a></p>\n'
        '{% endif %}\n'
        '{% if site.affiliate_bookshop_id %}\n'
        '<p><a href="https://bookshop.org/shop/{{ site.affiliate_bookshop_id }}" target="_blank" rel="nofollow">Shop on Bookshop.org</a></p>\n'
        '{% endif %}\n'
        '{% endblock %}'
    )

    # health.html
    (theme_dir / "health.html").write_text(
        '{% extends "base.html" %}\n'
        '{% block content %}\n'
        '<h2>Financial Health</h2>\n'
        '<p class="meta">Private page &middot; Not linked from the public site</p>\n'
        '<p>Monthly Prize Budget: ${{ prize_amount }}</p>\n'
        '{% endblock %}'
    )

    # CSS
    (theme_dir / "css" / "style.css").write_text(
        '*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }\n'
        'body { font-family: Georgia, "Times New Roman", serif; line-height: 1.7; color: #1a1a1a; background: #faf9f7; }\n'
        '.container { max-width: 960px; margin: 0 auto; padding: 0 1.5rem; }\n'
        'a { color: #2563eb; text-decoration: none; }\n'
        'a:hover { text-decoration: underline; }\n'
        'h1, h2, h3, h4 { font-family: "Segoe UI", system-ui, sans-serif; line-height: 1.3; color: #111; }\n'
        'h1 { font-size: 2rem; }\n'
        'h2 { font-size: 1.6rem; margin-bottom: 1rem; }\n'
        'h3 { font-size: 1.3rem; margin: 1.5rem 0 0.75rem; }\n'
        '.site-header { background: #1e293b; color: #fff; padding: 1rem 0; }\n'
        '.site-header a { color: #fff; }\n'
        '.site-header .logo h1 { color: #fff; font-size: 1.5rem; margin-bottom: 0.2rem; }\n'
        '.site-header .logo p { font-size: 0.85rem; opacity: 0.8; }\n'
        '.main-nav { display: flex; gap: 1.25rem; margin-top: 0.75rem; flex-wrap: wrap; }\n'
        '.main-nav a { font-size: 0.9rem; opacity: 0.9; }\n'
        '.main-nav a:hover { opacity: 1; text-decoration: underline; }\n'
        'main { padding: 2rem 0; min-height: 70vh; }\n'
        '.hero { text-align: center; padding: 3rem 0; }\n'
        '.hero h2 { font-size: 2.2rem; }\n'
        '.hero p { font-size: 1.1rem; color: #555; margin-top: 0.5rem; }\n'
        '.card { background: #fff; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }\n'
        '.card h3, .card h4 { margin-bottom: 0.5rem; }\n'
        '.meta { color: #666; font-size: 0.85rem; margin-bottom: 0.75rem; }\n'
        '.tag { display: inline-block; background: #e2e8f0; color: #475569; font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 3px; margin-right: 0.25rem; }\n'
        '.tag a { color: #475569; }\n'
        '.summary { background: #f1f5f9; border-left: 4px solid #2563eb; padding: 1rem; margin: 1rem 0; font-style: italic; }\n'
        '.content-body p { margin-bottom: 1rem; }\n'
        '.content-body h2 { margin-top: 2rem; }\n'
        '.content-body h3 { margin-top: 1.5rem; }\n'
        '.author-spotlight { background: #fef3c7; border: 1px solid #f59e0b; border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; text-align: center; }\n'
        '.btn { display: inline-block; background: #2563eb; color: #fff; padding: 0.5rem 1.25rem; border-radius: 6px; margin-top: 0.75rem; }\n'
        '.btn:hover { background: #1d4ed8; text-decoration: none; }\n'
        '.site-footer { background: #1e293b; color: #94a3b8; padding: 2rem 0; margin-top: 3rem; font-size: 0.85rem; }\n'
        '.site-footer a { color: #94a3b8; }\n'
        '.social-links { display: flex; gap: 1rem; margin-top: 0.5rem; }\n'
        '.tag-cloud { margin: 2rem 0; line-height: 2.2; }\n'
        '.aom-card { background: #fff; border-radius: 8px; padding: 2rem; text-align: center; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }\n'
        '.related { margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid #e2e8f0; }\n'
        'blockquote { border-left: 3px solid #cbd5e1; padding-left: 1rem; color: #475569; margin: 1rem 0; }\n'
        'pre { background: #1e293b; color: #e2e8f0; padding: 1rem; border-radius: 6px; overflow-x: auto; }\n'
        'code { font-family: "Fira Code", "Cascadia Code", monospace; font-size: 0.9rem; }\n'
        'img { max-width: 100%; height: auto; border-radius: 4px; }\n'
        'ul, ol { margin: 0 0 1rem 1.5rem; }\n'
        'li { margin-bottom: 0.3rem; }\n'
        'table { width: 100%; border-collapse: collapse; margin: 1rem 0; }\n'
        'th, td { padding: 0.5rem; border: 1px solid #e2e8f0; text-align: left; }\n'
        'th { background: #f1f5f9; }\n'
        '.content-page { max-width: 720px; margin: 0 auto; }\n'
        '@media (max-width: 640px) { .main-nav { flex-direction: column; gap: 0.5rem; } }'
    )


def _write_sample_plugins(root: Path):
    """Write sample plugin files."""
    plugins_dir = root / "plugins"

    # Reading Time Estimator plugin
    (plugins_dir / "reading_time.py").write_text(
        'from scholarscript.plugins import ScholarScriptPlugin\n\n'
        'class ReadingTimePlugin(ScholarScriptPlugin):\n'
        '    name = "reading-time"\n'
        '    version = "1.0.0"\n\n'
        '    def on_content_loaded(self, items):\n'
        '        for item in items:\n'
        '            words = len(item.body_md.split())\n'
        '            item.reading_time = max(1, round(words / 200))\n'
        '            if not item.summary:\n'
        '                item.summary = item.body_md[:200].strip() + "..." if len(item.body_md) > 200 else item.body_md.strip()\n'
    )

    # LaTeX Renderer plugin
    (plugins_dir / "latex_renderer.py").write_text(
        'from scholarscript.plugins import ScholarScriptPlugin\n\n'
        'class LaTeXRendererPlugin(ScholarScriptPlugin):\n'
        '    name = "latex-renderer"\n'
        '    version = "1.0.0"\n\n'
        '    def on_page_render(self, template_name, context):\n'
        '        if "item" in context and "$" in context["item"].body_html:\n'
        '            context["latex_enabled"] = True\n'
        '        return context\n'
    )


def _write_clone_profiles(root: Path):
    """Write default clone profile."""
    (root / "clone_profiles" / "default.json").write_text(
        '{\n'
        '  "include_images": true,\n'
        '  "include_css": false,\n'
        '  "include_js": false,\n'
        '  "max_pages": 50,\n'
        '  "respect_robots": true,\n'
        '  "user_agent": "ScholarScript/1.0 (Educational Purpose)",\n'
        '  "delay": 1.0,\n'
        '  "strip_selectors": ["script", "iframe", ".ad", ".adsense", "#google_ads"],\n'
        '  "exclude_patterns": ["/wp-admin", "/login", "/signup", "mailto:", "tel:"]\n'
        '}'
    )

    # Academic profile
    (root / "clone_profiles" / "academic.json").write_text(
        '{\n'
        '  "include_images": true,\n'
        '  "include_css": false,\n'
        '  "include_js": false,\n'
        '  "max_pages": 20,\n'
        '  "respect_robots": true,\n'
        '  "user_agent": "ScholarScript/1.0 (Academic Research)",\n'
        '  "delay": 2.0,\n'
        '  "strip_selectors": ["script", "iframe", ".ad", ".nav", ".sidebar", "footer", "header"],\n'
        '  "exclude_patterns": ["/wp-admin", "/login", "/signup", "/pdf", "/download"]\n'
        '}'
    )


def _write_github_templates(root: Path):
    """Write GitHub issue template and workflow files."""
    # Creative writing submission template
    template_path = root / ".github" / "ISSUE_TEMPLATE" / "creative-writing.yml"
    template_path.write_text(
        'name: Creative Writing Submission\n'
        'description: Submit your creative writing for the monthly prize\n'
        'title: "[Submission] Your Title Here"\n'
        'labels: [submission]\n'
        'body:\n'
        '  - type: input\n'
        '    id: title\n'
        '    attributes:\n'
        '      label: Title of Work\n'
        '      description: Enter the title of your creative writing piece\n'
        '    validations:\n'
        '      required: true\n'
        '  - type: textarea\n'
        '    id: body\n'
        '    attributes:\n'
        '      label: Body of Work\n'
        '      description: Paste your creative writing here\n'
        '    validations:\n'
        '      required: true\n'
        '  - type: input\n'
        '    id: author\n'
        '    attributes:\n'
        '      label: Full Name\n'
        '    validations:\n'
        '      required: true\n'
        '  - type: input\n'
        '    id: email\n'
        '    attributes:\n'
        '      label: Email Address\n'
        '    validations:\n'
        '      required: true\n'
        '  - type: input\n'
        '    id: paypal\n'
        '    attributes:\n'
        '      label: PayPal Email (for prize)\n'
        '    validations:\n'
        '      required: true\n'
        '  - type: input\n'
        '    id: pen_name\n'
        '    attributes:\n'
        '      label: Pen Name (optional)\n'
        '  - type: dropdown\n'
        '    id: genre\n'
        '    attributes:\n'
        '      label: Genre\n'
        '      options:\n'
        '        - Poetry\n'
        '        - Short Fiction\n'
        '        - Creative Non-Fiction\n'
        '        - Drama\n'
        '        - Other\n'
        '    validations:\n'
        '      required: true\n'
        '  - type: checkboxes\n'
        '    id: originality\n'
        '    attributes:\n'
        '      label: Originality Confirmation\n'
        '      options:\n'
        '        - label: I confirm this work is my original writing\n'
        '          required: true\n'
    )

    # GitHub Actions workflow for submission processing
    workflow_path = root / ".github" / "workflows" / "process-submission.yml"
    workflow_path.write_text(
        'name: Process Creative Writing Submission\n'
        'on:\n'
        '  issues:\n'
        '    types: [labeled]\n\n'
        'jobs:\n'
        '  process:\n'
        '    if: github.event.label.name == "submission"\n'
        '    runs-on: ubuntu-latest\n'
        '    steps:\n'
        '      - uses: actions/checkout@v3\n'
        '      - uses: actions/setup-python@v4\n'
        '        with:\n'
        '          python-version: "3.11"\n'
        '      - run: pip install scholarscript\n'
        '      - name: Process Submission\n'
        '        run: |\n'
        '          scholarscript process-submission "${{ github.event.issue.number }}"\n'
        '        env:\n'
        '          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}\n'
        '          AUTO_MODE: ${{ vars.AUTO_MODE || "true" }}\n'
        '      - name: Commit and Push\n'
        '        run: |\n'
        '          git config user.name "ScholarScript Bot"\n'
        '          git config user.email "bot@scholarscript.org"\n'
        '          git add .\n'
        '          git commit -m "Add submission #${{ github.event.issue.number }}" || true\n'
        '          git push\n'
    )

    # Deploy workflow
    workflow_deploy = root / ".github" / "workflows" / "deploy.yml"
    workflow_deploy.write_text(
        'name: Deploy to GitHub Pages\n'
        'on:\n'
        '  workflow_dispatch:\n'
        '    inputs:\n'
        '      message:\n'
        '        description: "Deploy message"\n'
        '        required: false\n'
        '        default: "Manual deploy"\n\n'
        'jobs:\n'
        '  deploy:\n'
        '    runs-on: ubuntu-latest\n'
        '    permissions:\n'
        '      contents: write\n'
        '    steps:\n'
        '      - uses: actions/checkout@v3\n'
        '      - uses: actions/setup-python@v4\n'
        '        with:\n'
        '          python-version: "3.11"\n'
        '      - name: Install dependencies\n'
        '        run: |\n'
        '          pip install scholarscript\n'
        '      - name: Build site\n'
        '        run: scholarscript build\n'
        '      - name: Deploy to GitHub Pages\n'
        '        uses: peaceiris/actions-gh-pages@v3\n'
        '        with:\n'
        '          github_token: ${{ secrets.GITHUB_TOKEN }}\n'
        '          publish_dir: ./public\n'
    )


if __name__ == "__main__":
    cli()
