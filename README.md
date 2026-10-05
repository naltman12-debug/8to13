# 8 to 13

US-listed companies grouped by market cap, from $10M to over $1T, with sector breakdowns.

## What's in here

| File | What it does |
|---|---|
| `template.html` | The website design. `build.py` fills it with data. |
| `build.py` | Downloads the latest listings, saves today's snapshot to `data/history.json`, and writes the finished site to `site/`. |
| `pipeline.py` | The filtering rules (US-based operating companies only, no SPACs, funds, preferreds or foreign ADRs) and the market-cap bands. |
| `backfill.py` | Optional, one time: rebuilds five years of daily history. |
| `data/history.json` | Saved snapshots. Starts with quarterly points back to October 2021 and grows by one entry per trading day. |
| `privacy.html` | Privacy page. Put your own email address in it before going live. |
| `.github/workflows/update.yml` | The schedule that rebuilds and republishes the site after every trading day. |

## Going live

1. Create a free GitHub account, then a new **public** repository named `8to13`.
2. Upload everything in this folder, including the hidden `.github` folder. On a Mac, press **Cmd + Shift + .** in Finder to show hidden folders before dragging them into GitHub's upload page.
3. In the repository, open **Settings → Pages** and set **Source** to **GitHub Actions**.
4. Open the **Actions** tab, choose **Update site**, and click **Run workflow**. Tick **backfill** the first time if you want daily history (it takes about an hour).
5. When it finishes, the site is live at `https://YOUR-USERNAME.github.io/8to13/`.

After that it updates itself every weekday evening. Nothing to run by hand.

## Your own domain

1. Buy the domain (Cloudflare Registrar, Porkbun or Namecheap).
2. In **Settings → Pages → Custom domain**, enter it and save.
3. At the registrar, add four `A` records for the bare domain pointing to
   `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`,
   and a `CNAME` record for `www` pointing to `YOUR-USERNAME.github.io`.
4. Once GitHub confirms the domain, tick **Enforce HTTPS**.

## Before turning on ads

- Switch `SOURCE_REPO` in `build.py` to a licensed data provider that allows commercial display. The current free source mirrors Nasdaq's screener and is fine for testing, not for a site that earns money.
- Update `privacy.html` to name the ad provider and its cookies.
- To update three times a day, use a provider with intraday data and swap in the three schedule lines already written (commented out) in `update.yml`.
