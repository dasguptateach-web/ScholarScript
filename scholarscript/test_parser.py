"""
ScholarScript Test Parser — detects MCQ papers with answer keys
and generates interactive test JSON data + content/tests/ entries.
Supports both table format (| Q | Ans |) and inline format (1. B 2. C ...)
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime

CONTENT_DIR = Path("content")
DATA_DIR = Path("data")
TESTS_CONTENT_DIR = CONTENT_DIR / "tests"

QUESTION_RE = re.compile(
    r'\*\*(\d+)\.\*\*\s*(.*?)\n\s*\(A\)\s*(.*?)\n\s*\(B\)\s*(.*?)\n\s*\(C\)\s*(.*?)\n\s*\(D\)\s*(.*?)(?=\n\s*\*\*\d+\.\*\*|\n\s*##|\Z)',
    re.DOTALL,
)

ANSWER_KEY_RE = re.compile(
    r'##\s*ANSWER\s*KEY.*?\n(.*?)(?=\n##|\Z)',
    re.DOTALL,
)

def try_parse_answer_key(text):
    answers = {}
    m = ANSWER_KEY_RE.search(text)
    if not m:
        return answers
    section = m.group(1)

    # Try table format: | Q | Ans | ...
    table_answers = {}
    for line in section.splitlines():
        line = line.strip()
        cells = [c.strip() for c in line.split("|") if c.strip()]
        if not cells:
            continue
        if cells[0] == "Q" and len(cells) >= 2:
            continue
        if cells[0].isdigit() and re.match(r'^[A-D]$', cells[1], re.IGNORECASE):
            table_answers[int(cells[0])] = cells[1].upper()
        for i in range(0, len(cells) - 1, 2):
            if cells[i].isdigit() and re.match(r'^[A-D]$', cells[i+1], re.IGNORECASE):
                table_answers[int(cells[i])] = cells[i+1].upper()
    if table_answers:
        return table_answers

    # Fallback: inline format — 1. B 2. B 3. C ... (possibly with ** markers)
    cleaned = re.sub(r'\*\*', '', section)
    inline_pat = re.compile(r'(\d+)\s*\.\s*([A-D])\s*')
    for m_ in inline_pat.finditer(cleaned):
        answers[int(m_.group(1))] = m_.group(2).upper()
    return answers

def try_parse_questions(text):
    questions = []
    for m in QUESTION_RE.finditer(text):
        qid = int(m.group(1))
        qtext = m.group(2).strip()
        opt_a = m.group(3).strip()
        opt_b = m.group(4).strip()
        opt_c = m.group(5).strip()
        opt_d = m.group(6).strip()
        questions.append({
            "id": qid,
            "question": qtext,
            "options": [opt_a, opt_b, opt_c, opt_d],
        })
    return questions

def slugify(title):
    s = title.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'[\s_]+', '-', s)
    return s[:80]

def process_paper(filepath):
    text = filepath.read_text(encoding="utf-8")
    # Only parse questions from the body BEFORE the answer key
    key_idx = text.find("## ANSWER KEY")
    body_text = text[:key_idx] if key_idx > 0 else text
    questions = try_parse_questions(body_text)
    if not questions:
        return None
    answers = try_parse_answer_key(text)
    if not answers:
        return None
    title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', text[:500], re.MULTILINE)
    title = title_match.group(1) if title_match else filepath.stem.replace("-", " ").title()
    date_match = re.search(r'^date:\s*["\']?(\S+?)["\']?\s*$', text[:500], re.MULTILINE)
    date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
    fm_end = text.find("---", 3)
    body = text[fm_end+3:].strip() if fm_end > 0 else text
    desc_match = re.search(r'^##\s+(.+)$', body, re.MULTILINE)
    description = desc_match.group(1) if desc_match else f"Practice test with {len(questions)} questions"
    marked = 0
    for q in questions:
        q["answer"] = answers.get(q["id"], None)
        if q["answer"]:
            marked += 1
    test_data = {
        "title": title,
        "slug": slugify(title),
        "date": date,
        "description": description,
        "total_questions": len(questions),
        "marked_answers": marked,
        "questions": questions,
    }
    return test_data

def write_test_data(test_data):
    if not test_data:
        return False
    slug = test_data["slug"]
    json_path = DATA_DIR / "tests" / f"{slug}.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    md_path = TESTS_CONTENT_DIR / f"{slug}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_content = (
        f"---\n"
        f"title: \"{test_data['title']}\"\n"
        f"date: {test_data['date']}\n"
        f"type: test\n"
        f"tags: [test, mcq, practice]\n"
        f"test_slug: {slug}\n"
        f"total_questions: {test_data['total_questions']}\n"
        f"---\n"
        f"## {test_data['title']}\n\n"
        f"{test_data['description']}\n\n"
        f"**{test_data['total_questions']} questions**"
        f" ({test_data['marked_answers']} with answer keys)\n\n"
        f"[Take the interactive test]({{{{ site.base_url }}}}/test/{slug}/)\n"
    )
    md_path.write_text(md_content, encoding="utf-8")
    return True

def main():
    papers_dir = CONTENT_DIR / "papers"
    if not papers_dir.exists():
        print("  No content/papers directory found.")
        return 0
    created = 0
    for f in sorted(papers_dir.glob("*.md")):
        try:
            data = process_paper(f)
            if data and write_test_data(data):
                print(f"  [TEST] {f.name} -> data/tests/{data['slug']}.json")
                created += 1
        except Exception as e:
            print(f"  [ERROR] {f.name}: {e}", file=sys.stderr)
    if created:
        print(f"  Created {created} test(s)")
    else:
        print("  No new tests created (no MCQ papers with answer keys found)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
