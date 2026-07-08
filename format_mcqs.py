"""
ScholarScript MCQ Formatter
Reformats crammed MCQs into proper multi-line format.
Handles:
  - **N.** and N. question numbering
  - All options on one line or each on its own line
  - Next Q number on same line as previous (D) option
Runs after scholarscript ingest and fix_tables.py.
"""
import re
import sys
from pathlib import Path

CONTENT_DIRS = [
    Path("content/papers"),
    Path("content/creative-writing"),
]

# Step 1: insert newline before any **N.** that is not at the start of a line
# but keep the first occurrence in the content (which may be inline after a header)
RE_INLINE_Q = re.compile(r'(?<!\n)(\*\*\d+\.\*\*)')

# Step 2: match **N.** + question + (A)..(D) options with optional line breaks
# Groups: 1=num, 2=question, 3=optA, 4=optB, 5=optC, 6=optD
RE_MCQ = re.compile(
    r'\*\*(\d+)\.\*\*\s*'                               # **N.**
    r'((?:(?!\s*\(A\)\b).)+?)'                           # question (lazy, until (A))
    r'\s*\(A\)\s*((?:(?!\s*\(B\)\b).)+?)'                # optA
    r'\s*\(B\)\s*((?:(?!\s*\(C\)\b).)+?)'                # optB
    r'\s*\(C\)\s*((?:(?!\s*\(D\)\b).)+?)'                # optC
    r'\s*\(D\)\s*((?:(?!\s*\*\*?\d+(?:\.\*\*|\.)\s|\s*##|\Z).)+?)',  # optD
    re.DOTALL
)


def separate_inline_questions(text: str) -> str:
    """Insert newline before any **N.** that appears mid-line."""
    lines = text.split('\n')
    result = []
    for line in lines:
        m = re.search(r'^(.*?)(\*\*\d+\.\*\*)', line)
        if m and m.group(1).strip():
            # There's non-whitespace before **N.** → split
            before, bold_q = m.group(1), m.group(2)
            rest = line[m.end(2):]
            result.append(before)
            result.append(bold_q + rest)
        else:
            result.append(line)
    return '\n'.join(result)


def format_mcqs_in_text(text: str) -> str:
    def replacer(m):
        num = m.group(1)
        question = m.group(2).strip().rstrip(':')
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
    return RE_MCQ.sub(replacer, text)


def fix_mcqs_in_file(filepath: Path) -> bool:
    text = filepath.read_text(encoding="utf-8")
    original = text
    text = separate_inline_questions(text)
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
