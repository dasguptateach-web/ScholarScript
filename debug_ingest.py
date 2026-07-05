from scholarscript.ingestion import IngestionEngine
from pathlib import Path
import os

os.chdir(r"C:\Users\81\AppData\Local\Temp\opencode\scholarscript")
uploads = Path("uploads")
content = Path("content")

print("=== Uploads dir:", uploads.resolve())
print("=== Files found:")
for f in sorted(uploads.iterdir()):
    if f.is_file():
        print(f"  {f.name} (suffix: {f.suffix.lower()})")
print()

engine = IngestionEngine(uploads, content)
print("=== Processing...")
results = engine.ingest_all()
print(f"Total results: {len(results)}")
for r in results:
    print(f"  [{r['status']}] {r['file']}")
    if r["status"] == "error":
        print(f"    Error: {r['error']}")
    elif r["status"] == "success":
        print(f"    -> {r['output']}")
