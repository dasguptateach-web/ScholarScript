"""
ScholarScript Table Fixer — converts pipe-delimited plaintext tables
into proper Markdown tables after ingestion.
Run after `scholarscript ingest`.
"""
import re
import sys
from pathlib import Path

CONTENT_DIRS = [
    Path("content/papers"),
    Path("content/creative-writing"),
]


def is_table_line(line: str) -> bool:
    """Check if a line looks like a pipe-delimited table row."""
    stripped = line.strip()
    if not stripped or stripped.startswith("|") or stripped.startswith("-"):
        return False
    parts = [p.strip() for p in stripped.split("|")]
    return len(parts) >= 3 and all(len(p) > 0 for p in parts)


def is_separator_row(line: str) -> bool:
    """Check if a line is a markdown table separator row (|---|---|)."""
    s = line.strip()
    return bool(re.match(r"^\|[\s:\-|]+\|?$", s)) and "---" in s


def proper_table_indices(lines: list) -> set:
    """Return indices of lines belonging to proper markdown tables
    (a | header row followed by a |---| separator row and | data rows).
    These must never be merged into single lines."""
    proper = set()
    i = 0
    n = len(lines)
    while i < n:
        if lines[i].lstrip().startswith("|") and i + 1 < n and is_separator_row(lines[i + 1]):
            j = i
            while j < n and lines[j].lstrip().startswith("|"):
                proper.add(j)
                j += 1
            i = j
        else:
            i += 1
    return proper


def fix_tables_in_file(filepath: Path) -> bool:
    """Fix pipe-delimited tables in a single markdown file."""
    text = filepath.read_text(encoding="utf-8")
    original = text
    lines = text.splitlines(keepends=False)

    # First pass: merge continuation lines that start with "|"
    # (if a table row was broken across lines) — but never merge lines
    # belonging to a proper markdown table (header + |---| + rows)
    proper = proper_table_indices(lines)
    merged = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if (
            i in proper
            or not (line.strip().startswith("|") and merged and merged[-1].strip().startswith("|"))
        ):
            merged.append(line)
        else:
            merged[-1] += " " + line.strip()
        i += 1
    lines = merged

    # Second pass: detect table blocks and wrap them
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if is_table_line(line) and not line.strip().startswith("|"):
            # Start of an unformatted table — collect all consecutive rows
            table_rows = [line]
            j = i + 1
            while j < len(lines) and is_table_line(lines[j]):
                table_rows.append(lines[j])
                j += 1

            # Parse into columns
            parsed = []
            for row in table_rows:
                cols = [c.strip() for c in row.strip().split("|")]
                parsed.append(cols)

            # Determine max column count
            max_cols = max(len(row) for row in parsed)

            # Normalize all rows to same column count
            for row in parsed:
                while len(row) < max_cols:
                    row.append("")

            # Output as proper markdown table
            first_row = parsed[0]
            result.append("| " + " | ".join(first_row) + " |")
            result.append("|" + "|".join("---" for _ in range(max_cols)) + "|")
            for row in parsed[1:]:
                result.append("| " + " | ".join(row) + " |")

            i = j
        else:
            result.append(line)
            i += 1

    # Third pass: fix rows that have a trailing "| |" (empty last col)
    out = []
    for line in result:
        if line.startswith("|") and line.endswith("| |"):
            line = line[:-2] + "|"
        out.append(line)

    text = "\n".join(out) + "\n"
    if text != original:
        filepath.write_text(text, encoding="utf-8")
        return True
    return False


def main():
    fixed_any = False
    for d in CONTENT_DIRS:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md")):
            try:
                if fix_tables_in_file(f):
                    print(f"  [FIXED] {f.name}")
                    fixed_any = True
            except Exception as e:
                print(f"  [ERROR] {f.name}: {e}", file=sys.stderr)

    if not fixed_any:
        print("  No tables needed fixing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
