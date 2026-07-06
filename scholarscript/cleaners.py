import re
from collections import Counter
from typing import List, Optional, Set, Tuple





PAGE_NUMBER_PATTERNS = [
    re.compile(r'^\s*\d+\s*$'),
    re.compile(r'(?i)^\s*page\s+\d+(\s+of\s+\d+)?\s*$'),
    re.compile(r'^\s*[-—–*•·■]\s*\d+\s*[-—–*•·■]\s*$'),
    re.compile(r'(?i)^\s*[\|\[\(]\s*page\s+\d+\s*[\|\]\)]\s*$'),
    re.compile(r'^\s*\d+\s*/\s*\d+\s*$'),
    re.compile(r'^\s*p\.?\s*\d+\s*$', re.IGNORECASE),
    re.compile(r'^\s*pp\.?\s*\d+[–\-]\d+\s*$', re.IGNORECASE),
    re.compile(r'^\s*[-—–*•·■]\s*\d+\s*[-—–*•·■]\s*$'),
]

HEADER_FOOTER_PATTERNS = [
    re.compile(r'(?i)^\s*[-—–]+\s*page\s+\d+\s+of\s+\d+\s*[-—–]+\s*$'),
    re.compile(r'(?i)^\s*[-—–]+\s*\d+\s*[-—–]+\s*$'),
    re.compile(r'(?i)^\s*(continued|cont\.?)\s*\.{0,3}\s*$'),
    re.compile(r'^\s*\.\.\.\s*\d+\s*\.\.\.\s*$'),
    re.compile(r'(?i)^\s*document\s+title\s*:?\s*$'),
]


def is_page_number(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    for pat in PAGE_NUMBER_PATTERNS:
        if pat.match(s):
            return True
    if len(s) <= 6 and s.isdigit():
        return True
    return False


def strip_inline_page_number(line: str) -> str:
    if is_page_number(line):
        return ""
    s = line.strip()
    m = re.match(r'^(\d{1,4})\s+(.{15,})', s)
    if m:
        return m.group(2).strip()
    m = re.match(r'^(.{15,})\s+(\d{1,4})$', s)
    if m:
        return m.group(1).strip()
    return line


def detect_repeating_lines(pages: List[str], threshold: float = 0.4) -> Set[Tuple[str, str]]:
    if len(pages) < 3:
        return set()
    first_counts: Counter = Counter()
    last_counts: Counter = Counter()
    second_counts: Counter = Counter()
    second_last_counts: Counter = Counter()
    for text in pages:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) < 2:
            continue
        first_counts[lines[0]] += 1
        last_counts[lines[-1]] += 1
        if len(lines) >= 3:
            second_counts[lines[1]] += 1
            second_last_counts[lines[-2]] += 1
    repeating: Set[Tuple[str, str]] = set()
    n = len(pages)
    for line, count in first_counts.items():
        if count / n >= threshold and len(line) > 3 and not is_page_number(line):
            repeating.add(("top", line))
    for line, count in second_counts.items():
        if count / n >= threshold and len(line) > 3 and not is_page_number(line):
            repeating.add(("top_2", line))
    for line, count in last_counts.items():
        if count / n >= threshold and len(line) > 3 and not is_page_number(line):
            repeating.add(("bottom", line))
    for line, count in second_last_counts.items():
        if count / n >= threshold and len(line) > 3 and not is_page_number(line):
            repeating.add(("bottom_2", line))
    return repeating


def clean_pdf_pages(page_texts: List[str]) -> List[str]:
    repeating = detect_repeating_lines(page_texts)
    if not repeating:
        for pat in HEADER_FOOTER_PATTERNS:
            has = any(pat.search(p) for p in page_texts)
    top_repeat: Set[str] = {t for (pos, t) in repeating if pos.startswith("top")}
    bottom_repeat: Set[str] = {t for (pos, t) in repeating if pos.startswith("bottom")}
    cleaned = []
    for text in page_texts:
        lines = text.split("\n")
        filtered = []
        for idx, line in enumerate(lines):
            s = line.strip()
            if not s:
                filtered.append("")
                continue
            if is_page_number(s):
                continue
            if idx < 4 and s in top_repeat:
                continue
            if len(lines) - idx <= 4 and s in bottom_repeat:
                continue
            if any(pat.match(s) for pat in HEADER_FOOTER_PATTERNS):
                continue
            filtered.append(s)
        cleaned.append("\n".join(filtered))
    return cleaned


def clean_text(text: str, pages: List[str] = None) -> str:
    if pages:
        cleaned_pages = clean_pdf_pages(pages)
        result = []
        for pg in cleaned_pages:
            lines = pg.split("\n")
            filtered = []
            for line in lines:
                stripped = strip_inline_page_number(line)
                if stripped:
                    filtered.append(stripped)
            result.append("\n".join(filtered))
        return "\n\n".join(result)
    lines = text.split("\n")
    filtered = []
    for line in lines:
        s = line.strip()
        if not s:
            filtered.append("")
            continue
        if is_page_number(s):
            continue
        if any(pat.match(s) for pat in HEADER_FOOTER_PATTERNS):
            continue
        stripped = strip_inline_page_number(s)
        if stripped:
            filtered.append(stripped)
    return "\n".join(filtered)
