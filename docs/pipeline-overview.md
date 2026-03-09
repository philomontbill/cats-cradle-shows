# Nightly Pipeline — How It Works

Plain-language walkthrough of the full nightly scrape-to-report pipeline.

Last updated: Mar 9, 2026

---

**Step 1.** GitHub Actions triggers the workflow at 3:30 AM ET (or manually via `gh workflow run`).

**Step 2.** Scrapers run, one per venue (14 scrapers, sequentially). For each venue scraper:

- **2a.** Scraper loads the venue's website and pulls every show listing (artist, date, opener, ticket link, image).

- **2b.** Scraper checks overrides first (`scrapers/overrides.json`). Overrides are the highest authority — if an artist has a manual override, it's applied immediately with no search. Three override types: `artist_youtube` (video assignments), `opener_youtube` (opener videos), `show_overrides` (artist/opener restructuring).

- **2c.** For non-overridden artists, scraper loads three reference files:
  - Previous scrape output (which artists already have a youtube_id)
  - Latest audit scores (how confident we are in each existing match)
  - Recent rejections from `video_states.json` (artists the verifier rejected in the last 7 days)

- **2d.** For each non-overridden artist, scraper asks: **should I search YouTube?**
  - If the artist was rejected by the verifier in the last 7 days → **skip, no API call**
  - If the artist already has a high-confidence match (audit score 70+) → **reuse the existing video, no API call**
  - If the artist has a low-confidence match (audit score < 70) → **search again, costs 100 quota units**
  - If the artist has no match at all → **search YouTube, costs 100 quota units**

- **2e.** If searching: scraper calls YouTube Search API with `"{artist} official music video"` (100 units). If no results, retries with `"{artist} band music"` (another 100 units).

- **2f.** Scraper scores up to 5 results by matching artist name against video title and channel name. Best score wins.

- **2g.** If the best score is 70+ → assign video as **unverified candidate** (user sees no-preview popup until verified). If score is 40-69 → flag. Below 40 → no video assigned.

- **2h.** Scraper saves the updated show data to `data/shows-{venue}.json`.

**Step 3.** Expire script runs. Removes shows with dates in the past.

**Step 4.** Monitor script runs. Checks scraper outputs for anomalies — 25% drop from previous night or below 20 total shows triggers alert.

**Step 5.** Validate script runs. Flags bad artist names, missing fields, suspicious patterns.

**Step 6.** Video verifier runs. For each artist that has an unverified youtube_id:

- **6a.** Skip if artist is overridden (locked by overrides.json) or already verified with the same video_id.

- **6b.** Call YouTube Videos API (1 quota unit) to get the video's title, view count, channel, upload date.

- **6c.** If that call returns 403 (quota exhausted) → **stop the entire verifier immediately**. All remaining videos keep their current status. No rejections on quota failure. *(Fixed Mar 9, 2026 — previously, 403 was treated as metadata failure, which silently rejected valid videos.)*

- **6d.** If metadata fetched, run checks:
  - Is the view count over the cap? (5M default, 20M for trusted session channels, 50M for trusted labels/VEVO, no cap for Topic channels)
  - Is the channel a trusted label or VEVO? If yes → bypass several checks.
  - Is the channel a trusted session channel (KEXP, Audiotree, NPR Music, Paste Magazine)? If yes → bypass mismatch/age but require artist name in video title.

- **6e.** Call YouTube Channels API (1 quota unit) to get subscriber count and channel name.

- **6f.** More checks:
  - Does the channel name match the artist? If no match AND artist name not in video title → **reject** (identity link check).
  - If no match AND 2M+ subscribers → **reject** (unless trusted).
  - Is the video 15+ years old AND channel doesn't match → **reject** (unless trusted).

- **6g.** If passes all checks → mark **verified** in `video_states.json`, video goes live on the site.

- **6h.** If fails any check → mark **rejected** in `video_states.json`, null out the youtube_id in the show data. Artist shows no-preview popup.

**Step 7.** Verifier generates the daily report:
- **7a.** Builds markdown report (GitHub Issue) and CSV with columns: Category, Artist, Role, Status, Venue, Date, Video URL, Detail, Definition, QC Pass/Fail.
- **7b.** Sends HTML email with CSV attachment.
- **7c.** Harvests any QC Pass/Fail marks from the previous day's Google Sheet (column J) and appends them to the persistent "QA Log" tab.
- **7d.** Writes fresh report to "Daily Video Reports" Google Sheet tab (replace, not append).
- **7e.** Updates Definitions tab if needed.

**Step 8.** Audit script runs. Checks every assigned video via oEmbed (free, no API key) and saves a timestamped accuracy snapshot.

**Step 9.** Git commit and push all changed files.

**Step 10.** If any step failed, a scrape-alert GitHub Issue is created listing which steps broke.

---

## Key Safety Mechanisms

### Override Authority Chain (Mar 5, 2026)
Overrides are checked FIRST in Step 2b, before any automated logic runs. The verifier also skips overridden artists. This means a manual override can never be overruled by the pipeline.

### Quota Exhaustion Protection (Mar 9, 2026)
Before this fix, a 403 from YouTube was treated as "could not fetch metadata" → video rejected → youtube_id nulled. A mid-run quota exhaustion could cascade and null every remaining video. Now the verifier detects 403 specifically and stops immediately, preserving all unchecked videos.

### should_search Variable Scope Fix (Mar 9, 2026)
The `should_search` variable in `base_scraper.py` was only defined in the non-override code path, but referenced later in progress output regardless. Overridden artists could trigger a NameError crash. Fixed by initializing `should_search = False` before the override check.

### Cascading Rejection Filter (Feb 27, 2026)
Before the rejection filter in Step 2d, a rejected artist would get its youtube_id nulled. The next night, Step 2d would see "no match" and re-search, burning 100 quota units to find the same video, which would get rejected again. Now Step 2d catches this and skips the search for 7 days.

### QC Tracking (Mar 9, 2026)
The daily report includes a blank "QC Pass/Fail" column. The user marks Pass/Fail during review. The next night, the pipeline harvests those marks before overwriting the sheet, appending them to a persistent "QA Log" tab for accuracy tracking over time.

---

## Future: Video Duration Check

The verifier does not currently check video duration. A podcast or livestream (60+ min) with a matching channel name could pass all checks. Adding `contentDetails` to the existing API call (zero extra quota cost) and flagging videos outside the 1-15 minute range would close this gap. Low priority — no false passes observed yet.
