"""One-time job: rebuild data/history.json with a snapshot for every trading day the
source dataset covers, using its own git history. Days are processed newest first so
older snapshots can reuse each company's later sector label.
Takes a while (roughly an hour). Run it from the Actions tab, or locally:  python backfill.py
"""
import json, subprocess, tempfile, datetime as dt, pathlib
from zoneinfo import ZoneInfo
from pipeline import companies, norm_sector, NEW_LABELS
from build import snapshot, SOURCE_REPO, ROOT

ET = ZoneInfo("America/New_York")
tmp = pathlib.Path(tempfile.mkdtemp())
subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", SOURCE_REPO, str(tmp)], check=True)
log = subprocess.run(["git", "-C", str(tmp), "log", "--format=%H %cI", "--", "nyse/nyse_full_tickers.json"],
                     capture_output=True, text=True, check=True).stdout.split("\n")
by_day = {}
for line in log:
    if not line.strip():
        continue
    sha, when = line.split()
    d = dt.datetime.fromisoformat(when).astimezone(ET).date()
    if d.weekday() < 5 and d not in by_day:   # git log is newest first, so this keeps the day's last update
        by_day[d] = sha
hist_path = ROOT / "data" / "history.json"
hist = {h["date"]: h for h in (json.load(open(hist_path)) if hist_path.exists() else [])}
tmap = {}   # ticker -> current-scheme sector, filled from newer days first
def save():
    hist_path.write_text(json.dumps(sorted(hist.values(), key=lambda h: h["date"]), separators=(",", ":")))
for i, (d, sha) in enumerate(sorted(by_day.items(), reverse=True)):
    if "sec" in hist.get(d.isoformat(), {}):
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
    cos = companies(rows)
    for c in cos:
        if c["sector"] in NEW_LABELS and c["sym"] not in tmap:
            tmap[c["sym"]] = c["sector"]
    hist[d.isoformat()] = snapshot(cos, d, tmap)
    if i % 50 == 0:
        print("done back to", d); save()
save()
print("Snapshots stored:", len(hist))
