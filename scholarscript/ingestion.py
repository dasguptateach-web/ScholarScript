import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from .models import ContentItem
from .parser import slugify


# ── Markdown formatting patterns for pasted/extracted text ──────────────
_BULLET_RE = re.compile(r'^[•●▪◦‣∙·※*+–—-]\s+(.+)$')
_NUM_ITEM_RE = re.compile(r'^(\d+)[\.\)]\s+(.+)$')
_LABEL_RE = re.compile(r"^([A-Z][A-Za-z'’\-]*(?:\s+[A-Za-z][A-Za-z'’\-]*){0,3})\s*:\s+(.+)$")
_STRUCT_HEAD_RE = re.compile(
    r'^(?:Stanza|Chapter|Section|Part|Act|Scene|Book|Appendix|Module|Unit|Topic)\b',
    re.IGNORECASE)


# Optional import guards
_HAS_DOCX = False
_HAS_PDF = False
_HAS_OCR = False
_HAS_ODT = False
_HAS_RTF = False
_HAS_TEX = False

try:
    from docx import Document
    _HAS_DOCX = True
except ImportError:
    pass

try:
    import pdfplumber
    _HAS_PDF = True
except ImportError:
    try:
        import PyPDF2
        _HAS_PDF = True
    except ImportError:
        pass

try:
    import pytesseract
    from PIL import Image
    import pdf2image
    _HAS_OCR = True
except ImportError:
    pass

try:
    from odf.opendocument import load as odf_load
    from odf.text import P
    _HAS_ODT = True
except ImportError:
    pass

try:
    import striprtf.striprtf as rtf_parser
    _HAS_RTF = True
except ImportError:
    pass

try:
    from tex import parse_latex
    _HAS_TEX = True
except ImportError:
    pass


class IngestionEngine:
    """Handles automatic ingestion of documents from /uploads into /content."""

    def __init__(self, uploads_dir: Path, content_dir: Path):
        self.uploads_dir = uploads_dir
        self.content_dir = content_dir
        self.processed_dir = uploads_dir / "processed"
        self.processed_dir.mkdir(exist_ok=True)
        self.results: List[dict] = []

    def ingest_all(self) -> List[dict]:
        """Process all unprocessed files in the uploads directory."""
        self.results = []
        supported = (".doc", ".docx", ".pdf", ".odt", ".rtf", ".txt", ".tex")

        for f in sorted(self.uploads_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in supported:
                result = self._process_single(f)
                self.results.append(result)

        return self.results

    def ingest_text(self, text: str, title: str = "", author: str = "",
                    content_type: str = "") -> dict:
        """Process raw pasted text through the same pipeline as uploaded files.

        Cleans the text, derives title/tags/DOI, converts to formatted
        Markdown and saves it to /content (papers or creative-writing).
        """
        from .cleaners import clean_text as ct

        result = {
            "file": "(pasted text)",
            "status": "pending",
            "title": "",
            "type": content_type or "paper",
            "output": "",
            "error": "",
        }

        try:
            text = ct(text or "")
            if not text.strip():
                result["status"] = "error"
                result["error"] = "Pasted text is empty"
                return result

            # Re-join hyphenated line-breaks (common when pasting from PDFs)
            text = re.sub(r"(\w)-\n([a-z])", r"\1\2", text)

            lines = text.strip().split("\n")

            # Derive title from the text itself unless one was supplied
            derived_title = (title or "").strip()
            body_start = 0
            if not derived_title:
                for i, line in enumerate(lines[:5]):
                    s = line.strip()
                    if not s:
                        continue
                    if re.match(r"^#{1,3}\s+\S", s):
                        derived_title = re.sub(r"^#{1,3}\s+", "", s).strip()
                        body_start = i + 1
                        break
                    if len(s) <= 90 and not s.rstrip().endswith((".", ",", ";", ":")):
                        derived_title = s
                        body_start = i + 1
                        break
                    break
            if not derived_title:
                first_sentence = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]
                words = first_sentence.split()
                derived_title = " ".join(words[:10]).rstrip(".,;:")
                if len(words) > 10:
                    derived_title += "..."
                derived_title = derived_title.title()

            # Strip a balanced pair of wrapping quotes from the title
            if (len(derived_title) >= 2 and derived_title[0] in '"“\''
                    and derived_title[-1] in '"”\''):
                derived_title = derived_title[1:-1].strip()

            body = "\n".join(lines[body_start:]).strip() if body_start else text.strip()

            content_type = content_type or self._detect_type(body)
            tags = self._extract_keywords(body, max_keywords=5)
            paper_url = self._extract_doi_or_link(text)
            date = datetime.now().strftime("%Y-%m-%d")
            md_body = self._text_to_markdown(body)

            # Drop a duplicate leading heading that repeats the title
            first_heading = re.match(r"^##\s+(.+)$", md_body, re.MULTILINE)
            if first_heading and first_heading.group(1).strip().lower() == derived_title.strip().lower():
                md_body = md_body[first_heading.end():].lstrip("\n")

            front_matter = self._build_front_matter(
                title=derived_title,
                date=date,
                tags=tags,
                content_type=content_type,
                paper_url=paper_url,
                author=author,
            )

            if content_type == "creative-writing":
                out_dir = self.content_dir / "creative-writing"
            else:
                out_dir = self.content_dir / "papers"
            out_dir.mkdir(exist_ok=True)

            slug = slugify(derived_title)
            out_path = out_dir / f"{slug}.md"
            n = 2
            while out_path.exists():
                out_path = out_dir / f"{slug}-{n}.md"
                n += 1

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(front_matter)
                f.write("\n")
                f.write(md_body)

            result["status"] = "success"
            result["title"] = derived_title
            result["type"] = content_type
            result["output"] = str(out_path)
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def _process_single(self, filepath: Path) -> dict:
        result = {
            "file": filepath.name,
            "status": "pending",
            "title": "",
            "type": "paper",
            "output": "",
            "error": "",
        }

        try:
            text, metadata = self._extract_text(filepath)
            if not text or not text.strip():
                result["status"] = "error"
                result["error"] = "No text could be extracted"
                return result

            title = self._derive_title(filepath, metadata)
            content_type = self._detect_type(text)
            tags = self._extract_keywords(text, max_keywords=5)
            paper_url = self._extract_doi_or_link(text)
            date = self._derive_date(filepath, metadata)
            md_body = self._text_to_markdown(text, source_ext=filepath.suffix.lower())

            front_matter = self._build_front_matter(
                title=title,
                date=date,
                tags=tags,
                content_type=content_type,
                paper_url=paper_url,
            )

            if content_type == "creative-writing":
                out_dir = self.content_dir / "creative-writing"
            else:
                out_dir = self.content_dir / "papers"
            out_dir.mkdir(exist_ok=True)

            slug = slugify(title)
            out_path = out_dir / f"{slug}.md"

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(front_matter)
                f.write("\n")
                f.write(md_body)

            # Move original to processed
            shutil.move(str(filepath), str(self.processed_dir / filepath.name))

            result["status"] = "success"
            result["title"] = title
            result["type"] = content_type
            result["output"] = str(out_path)

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def _extract_text(self, filepath: Path) -> Tuple[str, dict]:
        """Extract text and metadata from a document file."""
        ext = filepath.suffix.lower()
        metadata = {}

        if ext == ".txt":
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                from .cleaners import clean_text as ct
                return ct(f.read()), metadata

        elif ext == ".docx" and _HAS_DOCX:
            doc = Document(str(filepath))
            paras = []
            for p in doc.paragraphs:
                t = p.text.strip()
                if not t:
                    paras.append("")
                    continue
                style = p.style.name.lower() if p.style else ""
                if "heading" in style or "title" in style or "subtitle" in style:
                    level = re.search(r'heading\s*(\d+)', style)
                    prefix = "#" * min(int(level.group(1)) if level else 2, 6)
                    paras.append(f"{prefix} {t}")
                else:
                    paras.append(t)
            # Extract text from ALL tables
            table_texts = []
            for table in doc.tables:
                table_rows = []
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    if any(c for c in cells):
                        table_rows.append(" | ".join(cells))
                if table_rows:
                    table_texts.append("")
                    for line in table_rows:
                        table_texts.append(line)
            # Preserve paragraph breaks (double newline = paragraph boundary)
            text = "\n\n".join(paras)
            if table_texts:
                text = text + "\n\n" + "\n".join(table_texts)
            from .cleaners import clean_text as ct
            text = ct(text)
            # Extract metadata
            props = doc.core_properties
            if props:
                metadata["title"] = props.title
                metadata["author"] = props.author
                if props.created:
                    metadata["date"] = props.created.isoformat()[:10]
            return text, metadata

        elif ext == ".pdf":
            text = ""
            from .cleaners import clean_pdf_pages, clean_text as ct
            # Try pdfplumber with page-granularity paragraph preservation
            if not text.strip() and _HAS_PDF:
                try:
                    import pdfplumber
                    with pdfplumber.open(str(filepath)) as pdf:
                        raw_pages = []
                        for page in pdf.pages:
                            raw = page.extract_text() or ""
                            raw_pages.append(raw)
                        raw_pages = clean_pdf_pages(raw_pages)
                        page_texts = []
                        for raw in raw_pages:
                            page_texts.append(self._reflow_pdf_text(raw))
                        text = "\n\n".join(page_texts)
                except Exception:
                    pass
            # Fallback to PyPDF2
            if not text.strip():
                try:
                    import PyPDF2
                    with open(filepath, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        raw_pages = []
                        for page in reader.pages:
                            raw = page.extract_text() or ""
                            raw_pages.append(raw)
                        raw_pages = clean_pdf_pages(raw_pages)
                        page_texts = []
                        for raw in raw_pages:
                            page_texts.append(self._reflow_pdf_text(raw))
                        text = "\n\n".join(page_texts)
                except Exception:
                    pass
            if text.strip():
                return text, metadata

            # OCR fallback for scanned PDFs
            if _HAS_OCR:
                try:
                    from pdf2image import convert_from_path
                    import pytesseract
                    images = convert_from_path(str(filepath))
                    text = "\n\n".join(pytesseract.image_to_string(img) for img in images)
                    from .cleaners import clean_text as ct
                    return ct(text), metadata
                except Exception:
                    pass

            return "", metadata

        elif ext == ".odt" and _HAS_ODT:
            try:
                doc = odf_load(str(filepath))
                texts = [str(node) for node in doc.getElementsByType(P)]
                from .cleaners import clean_text as ct
                return ct("\n".join(texts)), metadata
            except Exception:
                pass

        elif ext == ".rtf" and _HAS_RTF:
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    text = rtf_parser.rtf_to_text(f.read())
                if text:
                    from .cleaners import clean_text as ct
                    return ct(text), metadata
            except Exception:
                pass

        elif ext == ".tex" and _HAS_TEX:
            try:
                text = parse_latex(filepath.read_text(encoding="utf-8"))
                from .cleaners import clean_text as ct
                return ct(text), metadata
            except Exception:
                # Fallback: extract text between { and } in \section{}, \subsection{}, etc.
                raw = filepath.read_text(encoding="utf-8")
                text = re.sub(r"\\(?:section|subsection|subsubsection|textbf|textit|emph)\{([^}]*)\}", r"\1", raw)
                text = re.sub(r"\\[a-zA-Z]+(\{[^}]*\})?", "", text)
                text = re.sub(r"[{}]", "", text)
                text = re.sub(r"%.*", "", text)
                from .cleaners import clean_text as ct
                return ct(text.strip()), metadata

        elif ext == ".doc":
            # .doc files require antiword or catdoc - try system call
            try:
                import subprocess
                result = subprocess.run(["antiword", str(filepath)], capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    from .cleaners import clean_text as ct
                    return ct(result.stdout), metadata
            except Exception:
                pass
            try:
                import subprocess
                result = subprocess.run(["catdoc", str(filepath)], capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    from .cleaners import clean_text as ct
                    return ct(result.stdout), metadata
            except Exception:
                pass

        return "", metadata

    def _derive_title(self, filepath: Path, metadata: dict) -> str:
        title = metadata.get("title", "")
        if title and len(title) > 2:
            return title.strip()
        name = filepath.stem
        name = re.sub(r"[-_]+", " ", name)
        name = re.sub(r"\s+", " ", name).strip()
        name = name.title()
        return name or "Untitled Document"

    def _derive_date(self, filepath: Path, metadata: dict) -> str:
        date = metadata.get("date", "")
        if date:
            return date
        try:
            mtime = filepath.stat().st_mtime
            return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        except Exception:
            return datetime.now().strftime("%Y-%m-%d")

    def _detect_type(self, text: str) -> str:
        """Auto-detect content type from text analysis."""
        lines = text.strip().split("\n")
        total_words = len(text.split())
        if total_words < 10:
            return "paper"

        # Check for poetic patterns (short lines, rhyming patterns)
        poetic_indicators = 0
        long_prose_lines = 0
        for line in lines[:50]:
            stripped = line.strip()
            if not stripped:
                continue
            word_count = len(stripped.split())
            if word_count <= 8:
                poetic_indicators += 1
            elif word_count > 20:
                long_prose_lines += 1

        sample_lines = min(len(lines[:50]), 50)
        if sample_lines > 0:
            poetry_ratio = poetic_indicators / sample_lines
            prose_ratio = long_prose_lines / sample_lines
            if poetry_ratio > 0.4 and prose_ratio < 0.2:
                return "creative-writing"

        return "paper"

    def _extract_keywords(self, text: str, max_keywords: int = 5) -> list:
        """Simple keyword extraction using YAKE-like approach (TF-based)."""
        import re
        from collections import Counter

        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        stopwords = {
            "the", "and", "for", "are", "but", "not", "you", "all", "can",
            "had", "her", "his", "him", "she", "its", "who", "was", "one",
            "our", "out", "has", "have", "been", "being", "were", "whom",
            "some", "them", "then", "than", "that", "this", "which", "what",
            "when", "where", "with", "will", "their", "there", "would",
            "about", "could", "should", "also", "into", "over", "such",
            "very", "just", "from", "they", "more", "these", "those",
            "upon", "within", "whose", "each",
        }
        words = [w for w in words if w not in stopwords and len(w) > 2]
        counter = Counter(words)
        return [w for w, _ in counter.most_common(max_keywords)]

    def _extract_doi_or_link(self, text: str) -> str:
        """Extract DOI, arXiv ID, or persistent URL from text."""
        doi_match = re.search(r'10\.\d{4,}/[-._;()/:A-Za-z0-9]+', text)
        if doi_match:
            doi = doi_match.group(0).rstrip(').,;:')
            return f"https://doi.org/{doi}"

        arxiv_match = re.search(r'arxiv:\s*(\d{4}\.\d+)', text, re.IGNORECASE)
        if arxiv_match:
            return f"https://arxiv.org/abs/{arxiv_match.group(1)}"

        url_match = re.search(r'https?://(?:dx\.)?doi\.org/\S+', text)
        if url_match:
            return url_match.group(0).rstrip(').,;:')

        return ""

    def _reflow_pdf_text(self, text: str) -> str:
        """Reflow PDF-extracted text to reconstruct paragraphs.

        PDF text extraction typically breaks each physical line with \n.
        This heuristic re-joins lines that belong to the same paragraph
        and inserts blank lines between logical paragraphs.
        Preserves question-answer patterns and intentional line structure.
        """
        lines = text.split("\n")
        blocks = []
        current = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current:
                    blocks.append(" ".join(current))
                    current = []
                continue

            # Hyphenated word-break
            if stripped.endswith("-") and len(stripped) > 3:
                current.append(stripped[:-1])
                continue

            is_short = len(stripped) < 45
            is_very_short = len(stripped) < 25
            starts_upper = stripped[0].isupper() if stripped else False
            previous_short = current and all(len(w) < 40 for w in current)
            ends_with_question = stripped.rstrip().endswith("?")
            looks_numbered = bool(re.match(r'^[\d\s\.\)\[\]QX]+$', stripped[:8]))

            if not current:
                current = [stripped]
            elif ends_with_question:
                current.append(stripped)
            elif is_very_short and starts_upper and not looks_numbered:
                blocks.append(" ".join(current))
                current = [stripped]
            elif previous_short and not is_short and starts_upper:
                blocks.append(" ".join(current))
                current = [stripped]
            elif is_short and starts_upper and not looks_numbered:
                blocks.append(" ".join(current))
                current = [stripped]
            else:
                current.append(stripped)

        if current:
            blocks.append(" ".join(current))

        return "\n\n".join(blocks)

    def _text_to_markdown(self, text: str, source_ext: str = "") -> str:
        """Convert pasted/extracted text to clean, structured Markdown.

        Handles:
        - blank-line-separated documents (docx/PDF extraction)
        - single-newline Word-style pastes (each line = full paragraph)
        - hard-wrapped PDF-style pastes (reflowed into paragraphs)

        Produces proper section headings (##/###), bullet and numbered
        lists, bold lead-ins ("Context:" ...), blockquoted poem excerpts
        and hard line breaks where line structure matters.
        """
        text = text.replace('\r\n', '\n').replace('\r', '\n').strip()
        if not text:
            return ""

        # Single-newline text (no blank lines at all)
        if "\n" in text and not re.search(r'\n[ \t]*\n', text):
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if lines and max(len(l) for l in lines) > 120:
                # Word-style paste: each line is a full paragraph
                text = "\n\n".join(self._group_single_newline(lines))
            else:
                # Hard-wrapped paste: reflow into paragraphs first
                text = self._reflow_pdf_text(text)

        blocks = re.split(r'\n[ \t]*\n', text)
        md_parts = []

        for block in blocks:
            lines = [l.strip() for l in block.split("\n") if l.strip()]
            if not lines:
                continue

            if len(lines) == 1:
                md_parts.append(self._format_paragraph(lines[0]))
                md_parts.append("")
                continue

            plain = [l for l in lines
                     if not self._is_bullet(l) and not _NUM_ITEM_RE.match(l)]
            long_ended = sum(
                1 for l in plain
                if len(l) > 60 and l.rstrip().endswith(('.', '!', '?', '”', '"')))
            word_style = bool(plain) and long_ended / len(plain) >= 0.5

            if word_style:
                # Each line is its own paragraph
                for l in lines:
                    md_parts.append(self._format_paragraph(l))
                    md_parts.append("")
            else:
                # Poem / list / Q&A: keep lines together with hard breaks
                md_parts.extend(self._format_structured_lines(lines))
                md_parts.append("")

        while md_parts and not md_parts[-1].strip():
            md_parts.pop()
        return "\n".join(md_parts) + "\n"

    # ── Markdown formatting helpers ─────────────────────────────

    def _is_bullet(self, s: str) -> bool:
        return bool(_BULLET_RE.match(s.strip()))

    def _looks_num_heading(self, s: str) -> bool:
        m = _NUM_ITEM_RE.match(s.strip())
        if not m:
            return False
        rest = m.group(2).strip()
        return len(rest.split()) <= 12 and not rest.rstrip().endswith(('.', '!', '?'))

    def _is_subheading(self, s: str) -> bool:
        words = s.split()
        if not (2 <= len(words) <= 12):
            return False
        if s.rstrip().endswith(('.', '!', '?', ',', ';', ':', '”', '"', "'")):
            return False
        if not s[:1].isalpha() or not s[:1].isupper():
            return False
        if s.startswith(('"', "'", '“', '#', '*', '(', '[', '•', '·', '–', '—')):
            return False
        if _STRUCT_HEAD_RE.match(s):
            return True
        caps = sum(1 for w in words if w[:1].isupper())
        if caps / len(words) >= 0.6:
            return True
        return s == s.upper() and len(s) >= 5

    def _is_poem_line(self, s: str) -> bool:
        if not s:
            return False
        if self._is_bullet(s) or _NUM_ITEM_RE.match(s):
            return False
        if len(s) > 90:
            return False
        if s.rstrip().endswith(('!', '?')):
            return False
        # Short period-ended lines can be verse (stanza endings);
        # long ones are prose paragraphs
        if s.rstrip().endswith('.') and len(s) > 60:
            return False
        if s[:1] in ('"', '“', '#', '*'):
            return False
        if self._is_subheading(s):
            return False
        return True

    def _format_bullet(self, s: str) -> str:
        m = _BULLET_RE.match(s.strip())
        if not m:
            return s.strip()
        item = m.group(1).strip()
        lm = _LABEL_RE.match(item)
        if lm and len(lm.group(1)) <= 32 and len(lm.group(2)) >= 10:
            return f"- **{lm.group(1)}:** {lm.group(2)}"
        return f"- {item}"

    def _format_paragraph(self, s: str) -> str:
        s = s.strip()
        if self._is_bullet(s):
            return self._format_bullet(s)
        m = _NUM_ITEM_RE.match(s)
        if m:
            rest = m.group(2).strip()
            if len(rest.split()) <= 12 and not rest.rstrip().endswith(('.', '!', '?')):
                return f"## {s}"
            return s
        if self._is_subheading(s):
            return f"### {s}"
        m = _LABEL_RE.match(s)
        if m and len(m.group(2)) >= 20:
            return f"**{m.group(1)}:** {m.group(2)}"
        return s

    def _group_single_newline(self, lines: list) -> list:
        """Group Word-style single-newline lines into logical blocks.

        Consecutive bullet lines, numbered items, quoted lines and
        poem-like lines stay together as one block; every other line
        becomes its own paragraph block.
        """
        blocks = []
        i, n = 0, len(lines)
        while i < n:
            l = lines[i].strip()
            if self._is_bullet(l):
                j = i
                while j < n and self._is_bullet(lines[j].strip()):
                    j += 1
                blocks.append("\n".join(x.strip() for x in lines[i:j]))
                i = j
            elif _NUM_ITEM_RE.match(l) and not self._looks_num_heading(l):
                j = i
                while (j < n and _NUM_ITEM_RE.match(lines[j].strip())
                       and not self._looks_num_heading(lines[j].strip())):
                    j += 1
                blocks.append("\n".join(x.strip() for x in lines[i:j]))
                i = j
            elif l[:1] in ('"', '“'):
                # Multi-line quotation: first line opens with a quote mark,
                # verse-like lines follow, last line closes with a quote mark
                j = i + 1
                closed = l.rstrip().endswith(('"', '”')) and len(l) > 1
                while j < n and not closed:
                    nxt = lines[j].strip()
                    if nxt[:1] not in ('"', '“') and not self._is_poem_line(nxt):
                        break
                    if nxt.rstrip().endswith(('"', '”')):
                        closed = True
                    j += 1
                blocks.append("\n".join(x.strip() for x in lines[i:j]))
                i = j
            elif self._is_poem_line(l):
                j = i
                while j < n and self._is_poem_line(lines[j].strip()):
                    j += 1
                if j - i >= 3:
                    blocks.append("\n".join(x.strip() for x in lines[i:j]))
                else:
                    blocks.extend(x.strip() for x in lines[i:j])
                i = j
            else:
                blocks.append(l)
                i += 1
        return blocks

    def _format_structured_lines(self, lines: list) -> list:
        """Format a poem/list/Q&A block: keep line structure with hard breaks."""
        out = []

        # Multi-line quotation (>= 2 lines): blockquote the whole block
        if len(lines) >= 2 and lines[0].strip()[:1] in ('"', '“'):
            for q in lines:
                out.append("> " + q.strip() + "  ")
            out.append("")
            return out

        i, n = 0, len(lines)
        while i < n:
            l = lines[i].strip()
            if self._is_bullet(l):
                while i < n and self._is_bullet(lines[i].strip()):
                    out.append(self._format_bullet(lines[i].strip()))
                    i += 1
                out.append("")
                continue
            f = self._format_paragraph(l)
            if f.startswith("##") or f.startswith("- ") or _NUM_ITEM_RE.match(f):
                out.append(f)
            else:
                out.append(f + "  ")
            i += 1
        return out

    @staticmethod
    def _yaml_escape(s: str) -> str:
        return s.replace('\\', '\\\\').replace('"', '\\"')

    @staticmethod
    def _yaml_quote(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def _build_front_matter(self, title: str, date: str, tags: list,
                            content_type: str, paper_url: str = "",
                            author: str = "") -> str:
        lines = ["---"]
        lines.append(f'title: "{self._yaml_escape(title)}"')
        lines.append(f"date: {date}")
        lines.append(f"type: {content_type}")
        if author:
            lines.append(f'author: "{self._yaml_escape(author)}"')
        if tags:
            lines.append(f"tags: [{', '.join(tags)}]")
        if paper_url:
            lines.append(f"paper_url: {self._yaml_quote(paper_url)}")
        lines.append("---")
        return "\n".join(lines)
