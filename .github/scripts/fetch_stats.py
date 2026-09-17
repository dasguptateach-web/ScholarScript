import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

BASE = "https://scholar.goatcounter.com/api/v0"

token = os.environ.get("GOATCOUNTER_TOKEN", "")
headers = {"Authorization": "Bearer " + token} if token else {}


def get(path):
    req = urllib.request.Request(BASE + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception:
        return None


now = datetime.now()
total = get("/stats/total")
today_data = get("/stats?period=" + now.strftime("%Y-%m-%d"))
month_data = get("/stats?period=" + now.replace(day=1).strftime("%Y-%m-%d"))

if total is None and today_data is None and month_data is None:
    print("GoatCounter API unavailable - keeping existing stats")
    raise SystemExit(0)

total = total or {}
today_data = today_data or {}
month_data = month_data or {}

total_count = total.get("count")
today_count = today_data.get("count")
month_count = month_data.get("count")

day_of_month = now.day
days_in_month = (
    (now.replace(month=now.month + 1, day=1) - now.replace(day=1)).days
    if now.month < 12
    else 31
)
day_of_year = (now - now.replace(month=1, day=1)).days + 1
days_in_year = (
    366 if now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0) else 365
)
avg = round(month_count / day_of_month) if month_count and day_of_month > 0 else 0

stats = {
    "today": today_count or 0,
    "month": month_count or 0,
    "year": round(month_count / day_of_year * days_in_year)
    if month_count and day_of_year > 0
    else 0,
    "total": total_count or 0,
    "daily_average": avg,
    "month_projection": avg * days_in_month,
    "updated": now.isoformat(),
    "note": "Stats will update when the GitHub Action runs. Enable public stats in GoatCounter for live data.",
}

Path("data").mkdir(exist_ok=True)
Path("data/visitor-stats.json").write_text(
    json.dumps(stats, indent=2) + "\n", encoding="utf-8"
)
print("Stats saved:", json.dumps(stats, indent=2))
