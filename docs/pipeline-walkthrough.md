# Nightly Pipeline — Complete Walkthrough

Plain-English, section-by-section walkthrough of every step in the nightly pipeline.

Last updated: Mar 7, 2026

---

## Pipeline Order

```
scrapers → expire → monitor → validate → verify videos → audit → commit
```

Triggered by GitHub Actions at 3:30 AM ET nightly, or manually via `gh workflow run scrape.yml`.

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
- The 25-show cap in 1g limits how many shows each venue processes per scrape. Most venue scrapers also have a fetch cap ([:25] or [:30]) that limits how many events are parsed from the website before processing. Both caps apply — the lower one wins.
- Show overrides in `overrides.json` can restructure scraped data — splitting combined artist names (e.g., "Band A and Band B" → headliner + opener), correcting artist/opener assignments, and adding notices. These are applied at the top of `process_shows_with_youtube()` before any search logic runs.
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

The verifier is the quality gate. It takes every unverified video candidate the scrapers found and decides: does this video actually belong to this artist? If yes, the video goes live on the site. If no, the video is removed and the artist shows a "No Preview" popup instead.

The verifier also builds the daily report — the main document you review each morning.

### 5a. Startup

The verifier loads four things:

1. **YouTube API key** — prefers `YOUTUBE_VERIFIER_API_KEY` (dedicated quota), falls back to `YOUTUBE_API_KEY` (shared with scrapers). Having a separate key means the verifier doesn't compete with the scrapers for quota.
2. **overrides.json** — manual overrides are locked. The verifier never touches them.
3. **video_states.json** — the verification state for every artist (verified, rejected, override, unverified). This is the verifier's memory of what it has already decided.
4. **All show data** — every `data/shows-*.json` file.

Before starting verification, it takes a snapshot of the current states. This is used later to detect "recoveries" — artists that were previously rejected but now pass with a different video.

### 5b. Main Loop

For each show across all venues, the verifier looks at both the headliner and the opener:

1. **Does the artist have a video?** If `youtube_id` is empty, skip — nothing to verify.
2. **Is the artist in overrides?** If yes, skip — overrides are locked. Count it for the report.
3. **Is the artist already verified with this same video?** If the video_id matches what was previously verified, skip — no need to re-check. Count it for the report.
4. **Otherwise** — this video needs verification. Proceed to the checks.

A 1-second pause between each verification prevents hitting YouTube's per-second rate limits. Each verification makes 2 API calls (1 unit each): one for video metadata, one for channel metadata. With ~60-70 unverified videos per night, that's ~140 quota units — well within the verifier's 10,000-unit daily budget.

### 5c. Verification Checks

The `verify_video()` function runs five checks against each candidate. It collects rejection reasons in a list — if the list is empty at the end, the video passes. If anything is in the list, the video is rejected.

**Check 1: Venue placeholder image** (free — no API call)
If the show's image URL contains a known venue placeholder filename (e.g., `cradlevenue.png` for Cat's Cradle), flag it. A venue using their own default artwork instead of the artist's artwork suggests this is an event listing, not a performing artist.

**Check 2: Video metadata** (1 quota unit)
Pull the video's title, channel name, channel ID, publish date, and view count from YouTube's `videos` endpoint. If this call fails, the video is immediately rejected — we can't verify what we can't see.

**Check 3: Channel metadata** (1 quota unit)
Pull the channel's name, subscriber count, and video count from YouTube's `channels` endpoint. This gives us context about who uploaded the video.

**Check 4: Evaluate all signals together**

These signals are evaluated using the video and channel metadata:

- **Topic channel?** YouTube auto-generates "{ArtistName} - Topic" channels. If the channel name matches this pattern and the artist name matches, it's a strong identity signal — skip the view count check entirely.

- **Trusted channel?** Normalize the channel name (lowercase, strip all non-alphanumeric characters) and check against three lists:
  1. **Labels** (14 known record labels: Nuclear Blast, Epitaph, etc.) — full trust. View cap raised to 50M, bypass channel mismatch and upload age checks.
  2. **VEVO** (normalized name ends with "vevo") — same full trust as labels.
  3. **Session channels** (KEXP, Audiotree, NPR Music, Paste Magazine) — semi-trusted. These channels host live performances by many different artists, so the channel name will never match the artist. Session channels bypass the channel mismatch and upload age checks, but require the artist name to appear in the video title. View cap set to 20M (between the 5M default and 50M for labels). If the artist name isn't in the title, the video is rejected — a session video we can't confirm belongs to the right artist isn't useful.

- **View count** — Default cap is 5M views. Labels/VEVO get 50M. Session channels get 20M. Topic channels with matching artist name have no cap. If the video exceeds its cap, it's rejected. The logic: bands playing 100-750 capacity venues rarely have videos with 5M+ views. A high view count on a non-matching channel usually means the scraper found a famous song by a different artist with a similar name.

- **Channel match** — Does the channel name relate to the artist name? (Normalized containment check — "artist in channel" or "channel in artist".) Evaluated in priority order:
  1. **Trusted label/VEVO** — skip the mismatch check entirely.
  2. **Session channel** — skip the subscriber check, but require artist name in the video title.
  3. **2M+ subscribers** — reject. A massive channel that doesn't match the artist name is almost certainly the wrong video.
  4. **Small channel, no match** — check if the artist name appears in the video title. If the artist name is in neither the channel name nor the video title, reject — there's no identity link at all. If the artist name is in the title, keep the video with a warning logged.

- **Upload date** — If the video is more than 15 years old AND the channel doesn't match the artist AND the channel isn't trusted or a session channel, reject. Very old videos with no channel connection are usually wrong matches. Trusted and session channels bypass this because they have legitimate older content.

**Check 5: Final decision**
If the rejection reasons list is empty, the video passed all checks. If anything is in the list, the video failed. This is deliberately conservative — failing any single check means rejection. The philosophy: a wrong video is worse than no video.

### 5d. After Verification

**If the video passed:**
- Update `video_states.json`: status = "verified", store the video_id, date, confidence signals, and all metadata.
- Add to tonight's "verified" list for the report.
- The video stays assigned in the show data — it's now live on the site.

**If the video failed:**
- Update `video_states.json`: status = "rejected", store the video_id, date, rejection reasons, and metadata.
- Add to tonight's "rejected" list for the report.
- **Null out the youtube_id in the show's JSON file.** This is the verifier's enforcement — the rejected video is removed from the show data. The artist will show a "No Preview" popup on the site until a better match is found or a manual override is added.
- The show file is rewritten only if something actually changed.

After processing all shows, the updated `video_states.json` is saved. Any null overrides (artists manually set to no video) are also marked in states so the report counts them correctly.

### 5e. Daily Report — GitHub Issue

The report has three sections:

**Section 1: Tonight's Delta**
A summary line showing counts: verified, rejected, recovered, unchanged, overrides. Then three tables:
- **Newly Verified** — artist, venue, date, confidence signals (channel match, Topic, label, view count)
- **Newly Rejected** — artist, venue, date, specific rejection reasons
- **Recovered** — artists that were previously rejected but passed tonight with a different video

**Section 2: Full Inventory**
Overall coverage stats (verified, rejected, no preview, override counts with percentages), then a per-venue breakdown showing how many shows have videos vs. total shows.

**Section 3: Quality Metrics**
Renamed from "Accuracy" (Mar 4, 2026). The original label was misleading — the audit's score measures whether the artist's name appears in the video title or channel name, not whether the video is truly correct for the artist. A video can score 95 (name match) and still be the wrong song. True accuracy requires manual review.

The section now reports two complementary metrics:
- **Match Confidence** — percentage of assigned videos scoring 70+ in name matching (from the audit, Step 6). A smoke detector: stable or rising means the system is working, a drop means investigate.
- **Coverage** — percentage of active shows that have a video assigned at all. Tracks how well the scrapers are finding matches.

Reading the two together tells the story: confidence stable + coverage rising = good. Confidence dropping = bad matches getting through. Coverage dropping = scrapers struggling.

Also shows average score, override count, and headliner vs. opener breakdown. Pulls historical data from accuracy_history.json for yesterday and 7-day average columns.

The report is posted as a GitHub Issue with the label `daily-video-report`. Before posting, the verifier closes any previous open issues with that label — so there's only ever one open daily report at a time. The CSV is saved to `qa/video-report-YYYY-MM-DD.csv`.

### 5f. Daily Report — CSV

The CSV has the same data as the GitHub Issue but in a flat format suitable for Google Sheets. Nine columns: Section, Artist, Role, Venue, Date, Video URL, Detail, Skip Reason, Definition.

**Skip Reasons** (what the pipeline decided for each artist):
- **verified** — Scored 70+ gate score and passed verifier checks. Assigned to show.
- **rejected** — Failed verifier checks. Link shows the rejected video; not assigned to show.
- **flag** — YouTube search scored 40-69. Assigned, flagged for review.
- **reused** — Prior match with high confidence kept from prior run. No new search.
- **filtered** — Scraper identified as non-searchable (event name, too short, invalid format).
- **no_results** — YouTube search ran but returned zero results.
- **api_error** — YouTube API or network error during search.
- **code_error** — Bug in scraper code during search.
- **no_log** — No search record found. Artist may not have been processed by the scraper.

**Definition column** — human-readable explanation of the skip reason for quick visual triage of the spreadsheet.

Three sections in each CSV:
- **Verified** — tonight's newly verified videos (excludes artists already verified in prior runs)
- **Rejected** — tonight's newly rejected candidates
- **No Preview** — split into two groups by a separator row:
  - **Actionable** (top) — items with skip reasons: flag, no_results, api_error, code_error. Need review.
  - **Already Reviewed** (bottom) — items with skip reasons: filtered, reused, no_log. Previously reviewed or not expected to have a video.
  - Artists already shown in the Rejected section are excluded from No Preview to avoid duplicates.

### 5g. Daily Report — Email and Sheets

After posting the GitHub Issue, the report is also delivered via two additional channels:

**HTML email** (via Gmail SMTP)
The markdown report is converted to styled HTML with inline CSS. The CSV is attached as a file. Sent from soundchecklocal@gmail.com using an app-specific password. The email includes a footer linking to the Google Sheet for full detail.

**Google Sheets** (via Sheets API)
The CSV data is written to the "Daily Video Reports" tab with a "Report Date" column prepended. The tab is replaced (not appended) each night — one clean copy with no duplicate rows. CSV row order is preserved (Verified → Rejected → Actionable No Preview → Already Reviewed No Preview).

Both delivery channels use graceful failure — if email or Sheets fails, a warning is printed but the pipeline continues. The GitHub Issue is the primary record.

### 5h. Accuracy History

After the report is posted, the verifier appends a snapshot to `qa/accuracy_history.json`. Each entry records: date, total shows, verified count, rejected count, no-preview count, override count, headliner and opener accuracy broken out separately, and the accuracy rate and average confidence from the latest audit.

This history is what powers the "yesterday" and "7-day average" columns in the Accuracy section of the report. It's also used by the weekly QC report for trend analysis.

### Key files
- `scripts/verify_videos.py` — the verifier (all logic above)
- `scripts/report_delivery.py` — shared email and Sheets utilities
- `qa/video_states.json` — verification state for every artist (read and updated)
- `qa/match_log.json` — scraper decisions (read for Skip Reason column)
- `qa/accuracy_history.json` — daily accuracy snapshots (appended)
- `qa/video-report-YYYY-MM-DD.csv` — CSV output per run

### Summary of Step 5

The verifier is the quality gate between the scrapers and the user. Every video the scrapers find goes through five checks. Passing all five means the video goes live. Failing any one means the video is removed and the artist gets a "No Preview" popup.

Key points:
- The verifier never modifies overrides — they're locked.
- Already-verified videos with the same video_id are skipped — no wasted API calls.
- The 1-second throttle between verifications keeps us under YouTube's per-second rate limits.
- The daily report is the main feedback loop — verified videos are spot-check opportunities, rejected candidates are calibration opportunities, and the No Preview queue is the manual review work queue.
- Three delivery channels (GitHub Issue, email, Sheets) ensure visibility. GitHub Issues are the audit trail, email is the morning notification, Sheets is the historical log.
- Accuracy history builds over time, enabling trend analysis in the weekly QC report.

---

## Step 6: Audit

The audit is an independent quality check. It asks a simple question for every video we've assigned: does the artist's name actually appear in the video's title or channel name? It scores each match and saves the results. The verifier (Step 5) uses the audit's accuracy numbers in the daily report.

### 6a. How It Works — oEmbed

The audit uses YouTube's oEmbed endpoint, which returns two things for any video ID: the video title and the channel name (called "author_name" in oEmbed). No API key required, no quota cost. The tradeoff is less data — oEmbed doesn't return view counts, subscriber counts, or publish dates. But for the audit's purpose (does the name match?), title and channel name are all it needs.

Each oEmbed call takes about 0.3 seconds. With ~200-250 active shows across all venues, a full audit takes about 1-2 minutes.

### 6b. Scoring

The `score_match()` function compares the artist name against the video title and channel name. It tries several matching strategies in order, returning the first one that hits:

1. **Artist name found in channel name** (95) — strongest signal. The channel belongs to the artist.
2. **Compact match with channel** (93) — same check but with all spaces and punctuation stripped. Catches "DRUG DEALER" matching "Drugdealer" or "MODEL / ACTRIZ" matching "ModelActriz".
3. **Artist name found in video title** (90) — good signal, but titles can contain other artist names too.
4. **Channel name found in artist name** (85) — reverse containment (short channel name inside longer artist name).
5. **VEVO or Topic channel match** (93) — if the channel ends with "VEVO" or "- Topic" and the base name matches the artist after stripping those suffixes.
6. **Compact match with title** (88) — collapsed-name check against the video title.
7. **Channel word overlap** (70-90) — at least 50% of the artist's words (3+ characters) found in the channel name. Score scales with overlap ratio.
8. **Title word overlap** (60-80) — same as above but against the video title. Lower scores because titles are noisier.
9. **Partial word overlap** (30-60) — any word overlap between artist name and the combined title/channel text.
10. **No match** (5) — nothing matched.

Before comparing, names go through normalization: lowercase, strip "the", remove tour suffixes, remove parentheticals, strip VEVO/Topic suffixes, remove punctuation, collapse whitespace.

### 6c. Per-Show Audit

For each active (non-expired) show across all venues:

- **Headliner with video** — fetch oEmbed, score the match, assign a confidence tier.
- **Headliner without video** — mark as "no_video" (no score possible).
- **Opener with video** — same as headliner. For openers with comma-separated names, only the first name is scored.
- **Opener without video** — mark as "no_video".

Confidence tiers:
- **High** (70+) — the name match is strong
- **Medium** (40-69) — partial match, worth reviewing
- **Low** (below 40) — weak match, likely wrong video
- **Error** — oEmbed call failed (video deleted, private, or YouTube hiccup)

### 6d. Summary Stats

After scoring every show, the audit computes:
- **Accuracy rate** — percentage of videos with high confidence (70+ score)
- **Average confidence** — mean score across all videos
- Per-venue breakdowns of the same

These numbers are what the verifier pulls into the daily report's Quality Metrics section (Step 5e).

### 6e. What "Accuracy" Actually Measures

Important caveat: the audit's "accuracy rate" measures **name similarity between artist and video**, not whether the video is truly correct. A video can score 95 (channel name contains artist name) and still be the wrong song by the right artist. Or a video can score 50 (partial word overlap) and actually be correct — just with a channel name that doesn't obviously match.

The audit catches the obvious wrong matches (artist name nowhere in the video or channel) but can't catch subtle wrong matches (right artist, wrong song; or a different artist with the same name). That's why the daily report exists as a manual review layer on top of the automated scoring.

### 6f. Output

The audit saves a timestamped JSON file to `qa/audits/YYYY-MM-DD_HHMM.json` containing:
- **Overall stats** — accuracy rate, average confidence, counts by tier
- **Per-venue stats** — same breakdown for each venue
- **Per-show entries** — every show with its artist, video, score, explanation, and tier

The verifier's `load_latest_audit()` function reads the most recent file from this directory to populate the Quality Metrics section of the daily report.

### Key files
- `qa/audit_accuracy.py` — the audit script
- `qa/audits/YYYY-MM-DD_HHMM.json` — timestamped audit snapshots

### Summary of Step 6

The audit is a second opinion. The scraper (Step 1) uses its own scoring to decide which video to assign. The verifier (Step 5) uses YouTube API data to decide whether to accept or reject. The audit independently re-checks every assignment by comparing the artist name against the video's actual title and channel name via oEmbed.

Key points:
- Zero API cost — uses oEmbed (free, no key required).
- Independent signal — different scoring logic from both the scraper and the verifier. Catches problems the other steps might miss.
- "Accuracy" is a proxy — it measures name matching, not true correctness. Manual review remains the final quality check.
- Historical snapshots enable trend analysis — is accuracy improving over time as we add overrides and tune thresholds?

---

## Step 7: Commit, Push, and Alert

After all processing steps finish, the pipeline commits the results to git and checks whether anything broke.

### 7a. Commit and Push

The GitHub Actions runner configures a bot identity (`github-actions[bot]`) and stages a specific set of files:

- `data/shows-*.json` — updated show data from all scrapers
- `logs/` — scrape history and report logs
- `qa/match_log.json` — scraper match decisions
- `qa/audits/` — tonight's audit snapshot
- `qa/video_states.json` — updated verification states
- `qa/video-report-*.csv` — tonight's CSV report
- `qa/validation_baseline.json` — updated warning hashes
- `qa/accuracy_history.json` — appended accuracy snapshot

Only these files are staged — not the entire repository. This prevents accidental commits of local-only files or configuration changes.

After staging, the pipeline checks if anything actually changed (`git diff --staged --quiet`). If nothing changed (rare — show dates shift almost every night), no commit is created. If there are changes, it commits with the message "Update show data YYYY-MM-DD".

Before pushing, it runs `git pull --rebase` to handle any commits that may have landed on main since the workflow started (e.g., a manual push during the pipeline run). Then it pushes to main. Since Vercel auto-deploys on push, this commit is what updates the live site.

### 7b. Alert on Failure

After the commit step, the pipeline checks whether any previous step failed. Every step in the pipeline uses `continue-on-error: true`, meaning a failure in one step doesn't stop the others — the pipeline always runs to completion. But failures still need attention.

The alert checks all 15 steps: 12 scrapers + monitor + validate + verify. If any of them failed, it creates a GitHub Issue (label: `scrape-alert`) with a table showing every step and its status (pass or fail), plus a link to the full workflow logs.

This is separate from the daily video report (which is an informational summary). The scrape alert only fires when something actually broke — a scraper crashed, the monitor detected a problem, or the verifier errored out.

### Key files
- `.github/workflows/scrape.yml` — the workflow definition (all steps above)

### Summary of Step 7

The commit step is mechanical — stage specific files, commit if changed, rebase, push. The push triggers a Vercel deploy, which updates the live site.

The alert step is the safety net. Because every step uses `continue-on-error: true`, the pipeline always runs from start to finish. The alert catches failures after the fact and creates a visible GitHub Issue so they don't go unnoticed.

Key points:
- Only specific files are staged — prevents accidental commits of local config or secrets.
- The commit only happens if files actually changed — no empty commits.
- `git pull --rebase` before push handles any concurrent commits gracefully.
- The Vercel deploy is automatic — the commit IS the deploy trigger.
- Alert issues are separate from daily reports — alerts mean something broke, reports are routine summaries.

---

## Known Issues — Resolved

### ~~No Preview Full Dump (Task #10)~~ — Fixed Mar 7, 2026
Daily Video Reports sheet is now replaced (not appended) each night. Rejected artists excluded from No Preview section. No more duplicate rows.

### ~~Duplicate "New" Verified Entries (Task #11)~~ — Fixed Mar 7, 2026
Previously-verified artists are now excluded from the Verified section. Only genuinely new verifications appear. The verifier already skipped re-verifying same video IDs (line 941-946), but the CSV builder was still listing artists re-verified with different video IDs at different venues.
