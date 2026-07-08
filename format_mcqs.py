"""
ScholarScript MCQ Formatter — reformats crammed MCQs into proper multi-line format.
Detects patterns like "1. question (A) opt (B) opt (C) opt (D) opt 2. ..."
and breaks them so each question + options are on separate lines.
Run after `scholarscript ingest` (and after fix_tables.py).
"""
import re
import sys
from pathlib import Path

CONTENT_DIRS = [
    Path("content/papers"),
    Path("content/creative-writing"),
]

MCQ_PATTERN = re.compile(
    r'(\d+)\.\s+'
    r'(.*?)'
    r'\(A\)\s+(.*?)'
    r'\(B\)\s+(.*?)'
    r'\(C\)\s+(.*?)'
    r'\(D\)\s+(.*?)'
    r'(?=\s*\d+\.\s+|\s*$|(?:\n\s*\n))',
    re.DOTALL
)

def format_mcqs_in_text(text: str) -> str:
    def replacer(m):
        num = m.group(1)
        question = m.group(2).strip()
        opt_a = m.group(3).strip()
        opt_b = m.group(4).strip()
        opt_c = m.group(5).strip()
        opt_d = m.group(6).strip()
        return (
            f"**{num}.** {question}\n"
            f"    (A) {opt_a}\n"
            f"    (B) {opt_b}\n"
            f"    (C) {opt_c}\n"
            f"    (D) {opt_d}"
        )
    return MCQ_PATTERN.sub(replacer, text)

def fix_mcqs_in_file(filepath: Path) -> bool:
    text = filepath.read_text(encoding="utf-8")
    original = text
    text = format_mcqs_in_text(text)
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
                if fix_mcqs_in_file(f):
                    print(f"  [FIXED] {f.name}")
                    fixed_any = True
            except Exception as e:
                print(f"  [ERROR] {f.name}: {e}", file=sys.stderr)
    if not fixed_any:
        print("  No MCQs needed reformatting.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
