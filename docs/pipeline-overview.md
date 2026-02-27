# Nightly Pipeline — How It Works

Plain-language walkthrough of the full nightly scrape-to-report pipeline.

Last updated: Feb 27, 2026

---

**Step 1.** GitHub Actions triggers the workflow at 11 PM ET (or manually via `gh workflow run`).

**Step 2.** Scrapers run, one per venue (11 scrapers, sequentially). For each venue scraper:

- **2a.** Scraper loads the venue's website and pulls every show listing (artist, date, opener, ticket link, image).

- **2b.** Scraper loads three reference files:
  - Previous scrape output (which artists already have a youtube_id)
  - Latest audit scores (how confident we are in each existing match)
  - Recent rejections from `video_states.json` (artists the verifier rejected in the last 7 days)

- **2c.** For each artist on the schedule, scraper asks: **should I search YouTube for this artist?**
  - If the artist was rejected by the verifier in the last 7 days → **skip, no API call**
  - If the artist already has a high-confidence match (audit score 70+) → **reuse the existing video, no API call**
  - If the artist has a low-confidence match (audit score < 70) → **search again, costs 100 quota units**
  - If the artist has no match at all → **search YouTube, costs 100 quota units**

- **2d.** If searching: scraper calls YouTube Search API with `"{artist} official music video"` (100 units). If no results, retries with `"{artist} band music"` (another 100 units).

- **2e.** Scraper scores up to 5 results by matching artist name against video title and channel name. Best score wins.

- **2f.** If the best score is 70+ → assign video as **unverified candidate** (user sees no-preview popup until verified). If score is 40-69 → flag. Below 40 → no video assigned.

- **2g.** Scraper saves the updated show data to `data/shows-{venue}.json`.

**Step 3.** Expire script runs. Removes shows with dates in the past.

**Step 4.** Monitor script runs. Checks scraper outputs for anomalies (missing data, sudden drops).

**Step 5.** Validate script runs. Flags bad artist names, missing fields, suspicious patterns.

**Step 6.** Spotify enrichment runs. For each artist across all venues:
- If artist is already cached (within 30 days) → skip
- If not cached → search Spotify API for the artist name
- If found → cache popularity, genres, followers, match confidence
- If not found → cache as `no_match`

**Step 7.** Video verifier runs. For each artist that has an unverified youtube_id:

- **7a.** Call YouTube Videos API (1 quota unit) to get the video's title, view count, channel, upload date.

- **7b.** If that call fails (e.g., 403 quota exhausted) → **reject** with "could not fetch metadata."

- **7c.** If it succeeds, run checks:
  - Is the view count over the cap? (5M default, higher for popular Spotify artists, no cap for trusted labels/VEVO/Topic channels)
  - Is the channel a trusted label or VEVO? If yes → bypass several checks.

- **7d.** Call YouTube Channels API (1 quota unit) to get subscriber count and channel name.

- **7e.** More checks:
  - Does the channel name match the artist? If no match AND 2M+ subscribers → **reject** (unless trusted).
  - Is the video 15+ years old AND channel doesn't match → **reject** (unless trusted).
  - Does Spotify say this artist doesn't exist (`no_match`) AND channel doesn't match → **reject** (unless trusted).

- **7f.** If passes all checks → mark **verified** in `video_states.json`, video goes live on the site.

- **7g.** If fails any check → mark **rejected** in `video_states.json`, null out the youtube_id in the show data. Artist shows no-preview popup.

**Step 8.** Verifier generates the daily report (markdown + CSV) and posts it as a GitHub Issue.

**Step 9.** Audit script runs. Checks every assigned video via oEmbed (free, no API key) and saves a timestamped accuracy snapshot.

**Step 10.** Git commit and push all changed files.

**Step 11.** If any step failed, a scrape-alert GitHub Issue is created listing which steps broke.

---

## The Cascading Failure (fixed Feb 27, 2026)

Before the rejection filter in Step 2c, a rejected artist in Step 7g would get its youtube_id nulled. The next night, Step 2c would see "no match" and re-search (Step 2d), burning 100 quota units to find the same video, which would get rejected again. Now Step 2c catches this and skips the search for 7 days.

## Future: Video Duration Check

The verifier does not currently check video duration. A podcast or livestream (60+ min) with a matching channel name could pass all checks. Adding `contentDetails` to the existing API call (zero extra quota cost) and flagging videos outside the 1-15 minute range would close this gap. Low priority — no false passes observed yet.
