"""Builds the 8 to 13 site.

1. Downloads the latest NYSE / Nasdaq / NYSE American listings.
2. Filters to US-based operating companies and groups them into market-cap bands.
3. Adds today's snapshot to data/history.json (one entry per trading day).
4. Writes site/index.html and site/privacy.html.

Run:  python build.py
"""
import json, re, statistics, collections, subprocess, tempfile, datetime as dt, pathlib, shutil
from zoneinfo import ZoneInfo
from pipeline import companies, band_stats, BANDS, sector_stats

ROOT = pathlib.Path(__file__).parent
SOURCE_REPO = "https://github.com/rreichel3/US-Stock-Symbols.git"   # replace with a licensed source before running ads
ET = ZoneInfo("America/New_York")
WINDOW_YEARS = 5

def fetch_latest():
    tmp = pathlib.Path(tempfile.mkdtemp())
    subprocess.run(["git", "clone", "-q", "--depth", "1", SOURCE_REPO, str(tmp)], check=True)
    when = subprocess.run(["git", "-C", str(tmp), "log", "-1", "--format=%cI"], capture_output=True, text=True, check=True).stdout.strip()
    rows = []
    for ex in ["nasdaq", "nyse", "amex"]:
        for r in json.load(open(tmp / ex / f"{ex}_full_tickers.json")):
            r["_ex"] = ex
            rows.append(r)
    shutil.rmtree(tmp, ignore_errors=True)
    # The source refreshes in the evening after the close, so the ET date of the update is the trading day.
    trading_day = dt.datetime.fromisoformat(when).astimezone(ET).date()
    return rows, trading_day

def clean_name(n):
    out = re.sub(r"\s*\(?(Class [A-Z]\s+)?(Common Stock|Common Shares|common stock|Common stock|Ordinary Shares|Capital Stock|Subordinate Voting Shares).*$", "", n).strip(" ,")
    return out or n

def bands_payload(cos):
    for x in cos:
        if x["sym"].startswith("BRK"):
            x["sector"] = "Finance"; x["sym"] = x["sym"].replace("/", ".")
        if x["sector"] in ("Miscellaneous", ""):
            x["sector"] = "Other"
        x["name"] = clean_name(x["name"])
    allmc = sum(x["mc"] for x in cos if x["mc"] >= 1e7)
    out = []
    for bid, name, lo, hi in BANDS:
        b = sorted([x for x in cos if lo <= x["mc"] < hi], key=lambda x: -x["mc"])
        caps = [x["mc"] for x in b]
        sec = collections.Counter(x["sector"] for x in b)
        out.append(dict(id=bid, band=name, lo=lo, hi=min(hi, 1e13), n=len(b),
                        median=statistics.median(caps) if caps else 0, mean=statistics.mean(caps) if caps else 0,
                        total=sum(caps), share=sum(caps) / allmc,
                        sectors={k: round(100 * v / len(b), 1) for k, v in sec.most_common()},
                        cos=[[x["sym"], x["name"], round(x["mc"] / 1e6, 1), x["sector"],
                              x["ex"].upper().replace("AMEX", "NYSE AMER")] for x in b]))
    return out

def snapshot(cos, day, tmap=None):
    bs, allv = band_stats(cos)
    return dict(date=day.isoformat(), total=round(allv / 1e6), n=[b["n"] for b in bs],
                share=[round(b["share"], 4) for b in bs], median=[round(b["median"] / 1e6, 1) for b in bs],
                sec=sector_stats(cos, tmap))

def page_points(hist):
    """Daily points for the last 100 days, one per week before that. Sector values go out in $B."""
    hist = sorted(hist, key=lambda h: h["date"])
    if not hist:
        return []
    recent = (dt.date.fromisoformat(hist[-1]["date"]) - dt.timedelta(days=100)).isoformat()
    weekly = {}
    for h in hist:
        if h["date"] < recent:
            weekly[dt.date.fromisoformat(h["date"]).isocalendar()[:2]] = h
    pts = sorted(weekly.values(), key=lambda h: h["date"]) + [h for h in hist if h["date"] >= recent]
    if pts[0] is not hist[0]:
        pts = [hist[0]] + pts
    out = []
    for h in pts:
        p = {k: h[k] for k in ("date", "total", "n", "share", "median")}
        if "sec" in h:
            p["sec"] = {s: r[:6] + [round(v / 1e3, 2) for v in r[6:]] for s, r in h["sec"].items()}
        out.append(p)
    return out

def chart_points(hist, today):
    """Keep the last five years: one point per month, plus the first and latest snapshot."""
    try:
        cutoff = today.replace(year=today.year - WINDOW_YEARS)
    except ValueError:                       # Feb 29
        cutoff = today.replace(year=today.year - WINDOW_YEARS, day=28)
    ordered = sorted(hist, key=lambda h: h["date"])
    inwin = [h for h in ordered if h["date"] >= cutoff.isoformat()]
    # Start from the last snapshot on or just before the cutoff (covers weekends and holidays).
    before = [h for h in ordered if h["date"] < cutoff.isoformat() and h["date"] >= (cutoff - dt.timedelta(days=7)).isoformat()]
    if before:
        inwin = [before[-1]] + inwin
    if not inwin:
        return []
    monthly = {}
    for h in inwin:
        monthly[h["date"][:7]] = h           # last snapshot of each month
    pts = {h["date"]: h for h in monthly.values()}
    pts[inwin[0]["date"]] = inwin[0]
    pts[inwin[-1]["date"]] = inwin[-1]
    return [pts[k] for k in sorted(pts)]

def main():
    rows, day = fetch_latest()
    cos = companies(rows)
    hist_path = ROOT / "data" / "history.json"
    hist = json.load(open(hist_path)) if hist_path.exists() else []
    snap = snapshot([dict(c) for c in cos], day)
    hist = [h for h in hist if h["date"] != snap["date"]] + [snap]
    hist.sort(key=lambda h: h["date"])
    hist_path.write_text(json.dumps(hist, separators=(",", ":")))

    payload = dict(bands=bands_payload(cos), hist=page_points(hist),
                   asof=f"{day.strftime('%B')} {day.day}, {day.year}, 4:00 PM ET")
    html = (ROOT / "template.html").read_text().replace("__DATA__", json.dumps(payload, separators=(",", ":")))
    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    (site / "index.html").write_text(html)
    shutil.copy(ROOT / "privacy.html", site / "privacy.html")
    print(f"Built site for {day}: {sum(b['n'] for b in payload['bands'])} companies, {len(hist)} snapshots stored.")

if __name__ == "__main__":
    main()
