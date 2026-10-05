"""One-time job: rebuild data/history.json with a snapshot for every trading day
in the last five years, using the source dataset's own git history.
Takes a while (roughly an hour). Run it once from the Actions tab, or locally:  python backfill.py
"""
import json, subprocess, tempfile, datetime as dt, pathlib
from zoneinfo import ZoneInfo
from pipeline import companies
from build import snapshot, SOURCE_REPO, ROOT, WINDOW_YEARS

ET = ZoneInfo("America/New_York")
tmp = pathlib.Path(tempfile.mkdtemp())
subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", SOURCE_REPO, str(tmp)], check=True)
log = subprocess.run(["git", "-C", str(tmp), "log", "--format=%H %cI", "--", "nyse/nyse_full_tickers.json"],
                     capture_output=True, text=True, check=True).stdout.split("\n")
today = dt.date.today()
cutoff = today.replace(year=today.year - WINDOW_YEARS - 1)
by_day = {}
for line in log:
    if not line.strip():
        continue
    sha, when = line.split()
    d = dt.datetime.fromisoformat(when).astimezone(ET).date()
    if d >= cutoff and d.weekday() < 5 and d not in by_day:   # git log is newest first, so this keeps the day's last update
        by_day[d] = sha
hist_path = ROOT / "data" / "history.json"
hist = {h["date"]: h for h in (json.load(open(hist_path)) if hist_path.exists() else [])}
for i, (d, sha) in enumerate(sorted(by_day.items())):
    if d.isoformat() in hist:
        continue
    rows = []
    try:
        for ex in ["nasdaq", "nyse", "amex"]:
            out = subprocess.run(["git", "-C", str(tmp), "show", f"{sha}:{ex}/{ex}_full_tickers.json"],
                                 capture_output=True, text=True, check=True).stdout
            for r in json.loads(out):
                r["_ex"] = ex
                rows.append(r)
    except Exception as e:
        print("skip", d, e); continue
    hist[d.isoformat()] = snapshot(companies(rows), d)
    if i % 50 == 0:
        print("done through", d)
        hist_path.write_text(json.dumps(sorted(hist.values(), key=lambda h: h["date"]), separators=(",", ":")))
hist_path.write_text(json.dumps(sorted(hist.values(), key=lambda h: h["date"]), separators=(",", ":")))
print("Snapshots stored:", len(hist))
