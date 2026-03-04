# Nightly Pipeline — Complete Walkthrough

Plain-English, section-by-section walkthrough of every step in the nightly pipeline.

Last updated: Mar 3, 2026

---

## Pipeline Order

```
scrapers → expire → monitor → validate → verify videos → audit → commit
```

Triggered by GitHub Actions at 11 PM ET nightly, or manually via `gh workflow run scrape.yml`.

---

## Step 1: Scrapers

Each venue has its own scraper that inherits from `scrapers/base_scraper.py`. The venue scraper handles getting show data from the venue's website. The base class handles everything after — cleaning artist names, finding YouTube videos, and deciding when to skip searches.

### 1a. Startup

When a scraper is created, it loads two things:
1. **overrides.json** — manual YouTube assignments for artists the automation can't handle (Model/Actriz, Drug Dealer, etc.)
2. **YouTube API key** — from environment or .env file

### 1b. Artist Name Cleaning

Before searching YouTube, the raw artist name goes through cleaning:
- First, check if it's an **event name**, not a band (Cabaret, Showcase, DJ Night, etc.) — if so, return nothing (no search)
- Strip **"Presents"** and everything after it
- Strip **everything after a colon** (tour/event info)
- Strip **tour suffixes** after dashes ("-- US Tour", "-- Album Release")
- Strip **parentheticals** ("(Acoustic Set)")
- Strip **feat.** suffixes
- Split **multi-artist bills** — take just the first name before commas, " / ", or "w/"

If after all that cleaning the name is less than 2 characters, no YouTube search is performed. The show appears as "No Preview" in the daily report.

### 1c. Gate Scoring

When YouTube returns search results, each candidate is scored 0-100 using simple if/then rules (not statistical analysis):
- **95**: Full artist name found inside the channel name (strongest signal — it's the artist's own channel)
- **85**: Channel name found inside the artist name
- **70-90**: Strong word overlap between artist name and channel name
- **75**: Multi-word artist name found in video title (decent but weaker)
- **50-70**: Partial word overlap with title
- **20**: Single-word artist name found in title only (very unreliable — "Nothing" matches Whitney Houston)
- **5**: No match at all

Score above 70 passes this gate. Scores 40-69 are flagged (video assigned but marked for review in the daily report). Below 40, the show appears as "No Preview" in the daily report.

### 1d. YouTube API Search (on gate scores above 70)

Two things work together on each search: the **search text** (what you're searching for, like typing into YouTube's search bar) and the **category filter** (a separate API parameter that tells YouTube to only return videos tagged under a specific category like Music, Sports, Gaming, etc.).

1. Search for `"{artist} official music video"` (search text) with Music category filter enabled (100 quota units). The category filter pre-screens results to only Music-tagged videos before the search text is even applied. Each search returns up to 5 candidates (we set this limit — YouTube allows 1 to 50, but the quota cost is the same regardless. Five gives enough variety to score without drowning in noise).
2. If zero results from step 1, retry without the Music category filter using `"{artist} band music"` (another 100 units). This is a fallback — it only runs when the first search comes back empty. Removing the category filter catches artists whose videos aren't categorized as Music by YouTube, which happens often with indie and smaller acts.
3. Score all 5 candidates from whichever search returned results (never 10 — only one search runs), pick the highest
4. Apply gate score thresholds:
   - **70+** = accept (assign the video)
   - **40-69** = flag (assign but mark for review)
   - **Below 40** = skip (appears as "No Preview" in the daily report)
5. If the API returns 403 (quota exhausted) or any other error, skip the artist and log the reason. The artist will appear as "No Preview" in the daily report — visible and actionable, rather than silently assigned a wrong video.

### 1e. Error Handling

If the API returns a quota error (403), any other HTTP error, or an exception, the scraper skips the artist and logs the reason to match_log.json. The artist will appear as "No Preview" in the daily report — visible and actionable.

### 1f. Smart Search Filtering

Before spending an API call on any artist, the scraper loads three reference files and uses them to make a definitive decision:

1. **video_states.json** (produced by Step 6) — Has the verifier rejected this artist? → Don't search. Permanent skip.
2. **Previous scrape output** — Does this artist already have a youtube_id from the last scrape?
   - No existing match → Search.
   - Has a match but no audit score → Keep it, don't waste a search.
3. **Latest audit scores** (produced by Step 7) — How strong is the existing match?
   - High gate score (70+) → Reuse, don't search.
   - Low gate score → Re-search to try for better.

### 1g. Process Shows

The main method every venue scraper calls: `process_shows_with_youtube(shows)`:
1. Load existing matches, audit scores, and rejections
2. For each show (up to limit of 25):
   - Apply any show-level overrides from overrides.json
   - Run smart filter on headliner — search or reuse?
   - Run smart filter on opener — search or reuse?
   - Log every decision to qa/match_log.json
3. Return the processed shows with youtube_id fields populated
4. Venue scraper saves result to `data/shows-{venue}.json`

### Key files
- `scrapers/base_scraper.py` — the engine (all logic above)
- `scrapers/overrides.json` — manual overrides (artist_youtube, opener_youtube, show_overrides)
- `scrapers/utils.py` — shared utilities (normalize, name_similarity, load_env_var)
- `data/shows-{venue}.json` — output per venue
- `qa/match_log.json` — every search decision logged

### Summary of Step 1

Every scrape pulls the venue website fresh and grabs whatever shows are currently listed. The scraper doesn't compare old vs new — if a show was cancelled or a date changed, it just reflects whatever the website says now.

Everything in Step 1 is about being efficient and accurate with YouTube searches: clean the artist name right (1b), score results honestly (1c), search smartly (1d), and don't search when we already have a good answer (1f). The goal is to not waste the ~100 daily API searches we get.

Key points:
- Overrides (1a) always win — checked before any smart filtering, never overwritten by automation.
- The 25-show cap in 1g limits how many shows each venue processes per scrape.
- Every decision is logged to match_log.json — search, reuse, skip, override — providing the audit trail for debugging.

---

## Step 2: Expire

Runs right after all scrapers finish. Loops through every venue's JSON file and marks past shows as expired.

### 2a. Parse Show Dates

Each show has a date string like "Fri, Feb 20". The script extracts the month and day, then assumes the current year. If it can't parse the date, it leaves the show alone.

Note: Year inference is simple — always uses current year. A show on "Sat, Jan 10" scraped in late December would be read as the current year (already past) and get expired, even if it's actually next year's show. Known simplification — hasn't caused problems yet, but worth watching as the calendar grows.

### 2b. Compare to Today

- Show date is before today → add `"expired": true` to that show.
- Show was previously expired but date is now today or future (venue corrected the date on their website) → remove the expired flag.
- Expired shows are **not deleted** — they stay in the JSON for historical data. They're just flagged.

### 2c. Recalculate Summary Counts

Updates three counts in each venue's JSON to reflect only active (non-expired) shows:
- `total_shows`
- `shows_with_video`
- `shows_with_image`

These counts are what the website uses to display venue stats. The file is only rewritten if something actually changed (avoids unnecessary git commits).

### Key files
- `scripts/expire_shows.py` — the expire script
- `data/shows-{venue}.json` — reads and updates each venue file

---

## Step 3: Monitor

Runs right after Expire. Compares tonight's show counts to last night's and fires alerts if something looks wrong. Think of it as a smoke detector — it doesn't fix problems, it tells you something might be broken.

### 3a. Load Previous Counts

The script reads `logs/scrape-history.json`, which stores the show count from the last run for each venue. If this file doesn't exist yet (first time the pipeline ever runs), the script starts with an empty history — every venue is treated as "no previous data" and no drop alerts can fire. New venues added later also show "no previous data" on their first night, then compare normally from the second night on.

### 3b. Count Tonight's Shows

Loops through every `data/shows-*.json` file and counts the total number of shows in each (including expired shows — this is a raw count of everything in the file, not just active shows). If a file can't be read or parsed, that venue gets a count of -1, which triggers an alert.

### 3c. Compare and Alert

Four things trigger an ALERT:

1. **File read/parse failure** (count = -1) — The venue's JSON file is corrupted or missing. Something broke during the scrape.
2. **Zero shows** — The scraper returned nothing. The venue website likely changed its layout, or the scraper errored out.
3. **Below 20 shows** — Most healthy venue calendars exceed our 25-show search limit. If a venue drops below 20, the scraper is likely missing a section of the page. This catches slow erosion that a percentage check would miss (e.g., 25 → 23 → 21 → 19 over four nights).
4. **25%+ drop** from the previous night — If a venue had 24 shows yesterday and only 17 tonight, that's a 29% drop. Likely means the scraper is only partially working or the site changed.

Checks 3 and 4 complement each other: the floor catches slow erosion, the percentage catches sudden drops.

Everything else is logged as normal — the venue name, current count, and previous count (or "no previous data" if this is the first time seeing that venue).

### 3d. Save and Log

Two outputs:

1. **scrape-history.json** — Overwritten every run with tonight's counts. This becomes "previous" for tomorrow's comparison.
2. **scrape-report.txt** — Appended every run. A running log of every monitor check with timestamps. Useful for spotting patterns over time (e.g., a venue that slowly drops from 25 → 20 → 15 shows over a week).

### 3e. Exit Code

If any alerts fired, the script exits with code 1. GitHub Actions uses this to trigger an alert Issue (label: `scrape-alert`). If everything is healthy, exits with code 0 — no alert.

### Key files
- `scripts/monitor_scrapes.py` — the monitor script
- `logs/scrape-history.json` — previous run's counts (overwritten nightly)
- `logs/scrape-report.txt` — running log of every monitor check

---

## Step 4: Validate

Runs after Monitor. Scans every active (non-expired) show across all venues looking for data quality problems. Think of Monitor as checking that the scrapers ran — Validate checks that the data they produced makes sense.

### 4a. Per-Show Checks

Each active show is checked for these issues, grouped into two severity levels:

**WARNING** (needs review):
1. **Long artist name** (60+ characters) — Likely a festival title or event description that slipped through name cleaning, not a band name.
2. **Event keywords in artist name** — Words like "Presents", "Festival", "Showcase", "Residency" suggest this is an event, not a performing artist.
3. **Cancelled/Postponed** — Keywords like "cancelled", "postponed", or "rescheduled" found in the artist name or show notice. The venue may have updated the listing but the show shouldn't be displayed.
4. **Opener contains "with"** — Suggests multiple bands crammed into one opener field (e.g., "Band A with Band B"). May need splitting.
5. **No video** — Show has no youtube_id. Expected for events and hard-to-match artists, but worth tracking.
6. **Missing required fields** — No date, no venue name, or no ticket URL. Basic data integrity.

**INFO** (low priority):
1. **Tour name in artist** — Colons or "Tour" in the artist name (e.g., "Peter McPoland: Big Lucky Tour"). The name cleaner should strip these, so this flags cases it missed.
2. **Opener no video** — Opener is listed but has no youtube_id. Common and expected — logged for awareness, not action.
3. **No image** — Show has no image URL. Just checks the field exists, doesn't verify the URL actually loads (that would be too slow).

### 4b. Cross-Venue Duplicate Check

After checking individual shows, the script looks across all venues for the same artist listed with different name spellings. It normalizes names (lowercase, strip "The ") and groups matches. If the same normalized name appears at multiple venues with different original spellings (e.g., "NIGHT MOVES" vs "Night Moves"), it flags a possible normalization issue.

Same artist at multiple venues with the same spelling is fine — that's just a touring band. Different spellings of the same name is the problem this catches.

### 4c. Baseline Comparison

The script doesn't alert on every warning every night — that would create noise. It maintains a baseline file (`qa/validation_baseline.json`) of previously seen warnings using hashes.

Each run:
1. Hash every current warning
2. Compare against the stored baseline
3. Categorize each warning as **NEW** (not in baseline), **KNOWN** (already seen), or **RESOLVED** (was in baseline, now gone)
4. Save current hashes as the new baseline

The output clearly separates these: "NEW: 3 | KNOWN: 12 | RESOLVED: 1"

### 4d. Exit Code

Exit code 1 only if there are **new** warnings — not for known ones. This means the GitHub Actions alert only fires when something changed, not every night for the same 12 known issues. Known warnings still print to the log for reference.

### Key files
- `scripts/validate_shows.py` — the validation script
- `qa/validation_baseline.json` — hashes of previously seen warnings (updated nightly)

### Why keep the validator?

Most of these checks overlap with the daily video report. Long artist names, event keywords, missing videos — these all surface naturally as "No Preview," verified, or rejected in the report. Cancelled/postponed shows resolve themselves within 24 hours (venue removes the listing, or expire handles the date). The cross-venue duplicate check (4b) is the only one that catches something genuinely outside the other steps' visibility.

So why keep it? It costs nothing — no API calls, no external requests, runs in under a second on local JSON files. The pipeline continues even if it crashes (`continue-on-error: true`). The baseline system prevents noise by only alerting on new warnings.

The data has future value. Over time, the warning history shows which scrapers produce the most data quality issues, which problem types recur, and which venues consistently need attention. That pattern data is useful for deciding where to invest scraper improvements as we add venues.

Decision: leave it as-is. Low cost, no risk, and the historical data earns its place.

---

## ~~Step 5: Spotify Enrichment~~ — Removed

**Removed Mar 4, 2026.** Spotify enrichment searched Spotify for each artist to confirm identity and provide popularity-based view count caps.

After evaluating its effectiveness: out of 414 total verified/rejected videos, Spotify's unique contribution was 10 rejections (2.4%) that no other check would have caught. All 10 were correct rejections (events and multi-artist bills), but 2.4% marginal value doesn't justify the dependency — those 10 rejections would simply appear in the daily report and add nominally to the manual review load. Additionally, every Spotify API call is visible to Spotify — a major potential competitor in the music discovery space. No reason to draw their attention to our work.

**What changed when removed:**
- View count caps simplified: 5M default, 50M for trusted labels/VEVO. No more popularity-based tiers.
- Spotify column removed from daily report tables and CSV.
- The `scripts/spotify_enrich.py` script and `qa/spotify_cache.json` cache are no longer used by the pipeline.
- Decommissioning: delete the "Local Soundcheck" app on developer.spotify.com, remove GitHub Secrets (`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`), remove from local `.env`.

---

## Step 5: Video Verifier

*To be documented during walkthrough*

---

## Step 6: Audit

*To be documented during walkthrough*

---

## Step 7: Commit & Report Delivery

*To be documented during walkthrough*

---

## Known Issues

### No Preview Full Dump (Task #10)
The No Preview section of the daily report iterates ALL shows without a youtube_id every night, writing ~80+ rows regardless of whether anything changed. The report never shrinks. Google Sheets accumulates duplicate No Preview rows nightly. Fix: add delta logic to only report new or changed entries.

### Duplicate "New" Verified Entries (Task #11)
Some artists (Los Straitjackets, Reverend Horton Heat) appear as "New" verified on consecutive nights for the same venues and dates. Either the video_id changes between scrapes, or the artist key doesn't match exactly. Wastes API calls and creates duplicate Sheet rows.
