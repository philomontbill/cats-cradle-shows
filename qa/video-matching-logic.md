# Video Matching Logic

## Background

Local Soundcheck shows YouTube video previews for upcoming artists at small venues. Getting the right video is critical — a wrong video (e.g., a Hank Williams song instead of the NC bluegrass band "Six More Miles") erodes user trust. No video (a "no preview" popup) is always preferable to the wrong video.

This document captures the design decisions and logic for how we find, verify, and assign YouTube videos to artists.

## Problem with the Original System

The original scraper (`base_scraper.py`) did three jobs at once: scraping venue websites, searching YouTube, and deciding whether to trust the result. Issues:

1. **No verification gate** — the scraper's confidence score (70+ = accept) was the only check. A video went live the moment the scraper assigned it. Users saw wrong matches before anyone could catch them.

2. **No concept of "intentionally no video"** — when we manually nulled out a wrong video, the smart filter saw `youtube_id: null` and treated the artist as brand new, re-searching and re-assigning the same wrong video the next night.

3. **Pure string matching** — the only signals were whether the artist name appeared in the video title or channel name. No view count, upload date, or channel analysis. "Six More Miles" matched a Hank Williams song because the title contained all three words.

4. **Aggressive coverage bias** — the system tried hard to find something for every band. This is backwards for our product. Coverage should grow organically as matches are verified, not forced.

## New Architecture: Three Separate Concerns

### 1. Scraper (existing base_scraper.py, modified)
- Scrapes venue websites for show data (dates, artists, openers, ticket URLs)
- Applies show-level overrides (festival names to real band names)
- Cleans artist names (strip tour suffixes, split multi-artist, detect event names)
- Searches YouTube API to find candidate videos for new/unverified artists
- Does NOT make the final assignment. Tags new matches as "unverified" with the candidate stored separately
- Preserves existing verified and overridden video assignments — never overwrites them

### 2. Verifier (new script, runs after scraper)
- Only looks at unverified candidates
- Runs multi-step checks against each candidate (see Verification Pipeline below)
- Promotes passing candidates to "verified" (video goes live)
- Rejects failing candidates (no-preview popup assigned)
- Logs everything for the daily report

### 3. Daily Video Report (new, runs after verifier)
- Summarizes tonight's changes
- Lists newly verified videos (spot-check opportunities)
- Lists rejected candidates with reasons (calibration opportunities)
- Shows full no-preview queue (manual review work queue)

This separation means we can iterate on verification logic without risking scraper stability, and we can run the verifier independently for manual reviews.

## Video States

Each artist's video assignment is in one of three states:

| State | Meaning | Can be overwritten? |
|-------|---------|-------------------|
| **Override** | You or I manually picked this video (or manually set null). Stored in `overrides.json`. | Only by another manual override |
| **Verified** | Passed the automated verification pipeline. | No — locked in until show expires or manual override |
| **Unverified** | Scraper found a candidate but verifier hasn't checked it yet. Shows no-preview popup until verified. | Yes — by the verifier promoting or rejecting it |

Key principle: **users never see an unverified match.** The no-preview popup is the default until a video is verified or overridden.

## Decision Tree (Full Logic Path)

### Phase 1: Scraper — Schedule Updates
1. Scrape venue website for current show listings
2. Apply show-level overrides (e.g., "Carrboro Bluegrass Festival Presents..." becomes artist: "Six More Miles", opener: "North State Grass")
3. Update schedule data: new shows, date changes, cancellations, new openers
4. For each artist, check video state:
   - **Override exists?** Use it (including null). Done.
   - **Already verified?** Keep it. Done.
   - **New artist or previously rejected?** Proceed to candidate search.

### Phase 2: Scraper — YouTube Candidate Search
5. Clean artist name (strip tour info, colons, "Presents", "feat.", split multi-artist on comma/" / "/"w/")
6. Check event keywords on original name (Cabaret, Showcase, DJ Night, etc.) — if match, skip (not a band)
7. Check manual overrides for cleaned name
8. Search YouTube API: `"{artist} official music video"` with Music category filter (100 quota units)
9. If no results, retry: `"{artist} band music"` without category filter (100 quota units)
10. Score each candidate (up to 5) using string matching:
    - Channel name contains artist name → 95
    - Artist name contains channel name → 85
    - 50%+ channel word overlap → 70-90
    - Multi-word artist in title → 75
    - Single-word artist at title start → 55
    - Partial matches → 20-45
    - No match → 5
11. Pick highest-scoring candidate. Store as unverified with candidate ID, score, and explanation. **Do not assign to youtube_id yet.** User sees no-preview popup.

### Phase 3: Verifier — Multi-Step Validation
12. For each unverified candidate, pull video metadata from YouTube `videos` endpoint (1 quota unit):
    - **View count check** — reject if views exceed threshold (~2-3M). A band at Cat's Cradle Back Room doesn't have a 40M-view video. This catches famous-song-name collisions (Six More Miles, Nothing, Heated).
    - **Upload date check** — flag if video age doesn't fit a current touring artist. A video from 2005 for a band playing next week warrants suspicion.
13. Pull channel info from YouTube `channels` endpoint (1 quota unit):
    - **Channel analysis** — is this the artist's own channel, or a compilation/covers/topic channel? Does the channel name relate to the artist?
14. Apply confidence threshold with all signals combined:
    - **Pass all checks** → promote to "verified," assign youtube_id, video goes live
    - **Fail any check** → reject, assign no-preview, log the reason
15. Rejected candidates and their reasons are preserved for the daily report

### Phase 4: Daily Video Report
16. Generate report covering:
    - **Tonight's Changes** — summary counts (new shows, verified, rejected, expired)
    - **New Verified Videos** — what passed and went live (with confidence and check results)
    - **Rejected Candidates** — what the scraper found but the verifier refused, with specific reasons (this is how we learn and calibrate)
    - **No Preview Queue** — full running list of all artists currently showing the popup, with status (override, rejected, no results, etc.)
17. Post as GitHub Issue (triggers email notification)

## Report Format

```
LOCAL SOUNDCHECK — DAILY VIDEO REPORT
Feb 24, 2026

TONIGHT'S CHANGES
  New shows added: 3
  Videos verified: 2
  Videos rejected: 1
  Shows removed/expired: 1

NEW VERIFIED VIDEOS
Artist           | Venue              | Date     | Video ID    | Confidence
-----------------+--------------------+----------+-------------+-----------
Waxahatchee      | Cat's Cradle       | Mar 15   | dK3qT5r0cMc| 95 (channel match)
Slow Teeth       | CC Back Room       | Mar 18   | a8Fk29xL4pQ| 88 (channel + low views)

REJECTED CANDIDATES
Artist           | Venue              | Date     | Candidate   | Reason
-----------------+--------------------+----------+-------------+---------------------------
Some Band        | Local 506          | Mar 16   | 82fR-6N0JQc | 12M views (cap: 2M)

NO PREVIEW QUEUE (7 total)
Artist           | Venue              | Date     | Status
-----------------+--------------------+----------+---------------------------
Six More Miles   | CC Back Room       | Feb 25   | Override: no video
Some Band        | Local 506          | Mar 16   | Rejected: view count
Another Act      | Pinhook            | Mar 17   | No results found
Heated           | Motorco            | Mar 20   | Rejected: matched H.E.A.T
Nothing          | Cat's Cradle       | Mar 22   | Rejected: single-word ambiguous
DJ Night         | Kings              | Mar 25   | Event name, not a band
North State Grass| CC Back Room       | Feb 25   | Opener: no results found
```

## Quota Budget

YouTube Data API free tier: 10,000 units/day.

| Operation | Cost | Typical nightly volume | Total |
|-----------|------|----------------------|-------|
| Search (new artists only) | 100 units | 5-10 searches | 500-1,000 |
| Video metadata (verify) | 1 unit | 5-10 videos | 5-10 |
| Channel info (verify) | 1 unit | 5-10 channels | 5-10 |
| **Total** | | | **~510-1,020** |

Well within the 10,000 daily limit. The key savings come from only searching new/unverified artists, not re-searching the full catalog every night.

## Root Cause: Why Six More Miles Kept Getting Overwritten

The `_load_existing_matches()` function in `base_scraper.py` (line 393-394) only loads artists into the "existing matches" dictionary if `youtube_id` is truthy:

```python
if artist and yt_id:
    matches[artist] = yt_id
```

When we manually set `youtube_id: null`, the artist was excluded from existing matches. The smart filter then treated it as a "new artist" and re-searched YouTube, finding the same wrong Hank Williams video every night.

The fix: the new system treats "verified" and "override" as durable states stored separately from the youtube_id field itself. A null override means "I chose no video" — not "please search again."

## Design Principles

1. **No video is better than wrong video** — the no-preview popup is an acceptable user experience. A wrong video is not.
2. **Confirmed videos are immutable** — once verified or overridden, the nightly scrape cannot change them.
3. **The daily report is a feedback loop** — rejected candidates teach us where the rules are too tight. Wrong matches that slip through teach us where they're too loose.
4. **Separation of concerns** — scraper finds candidates, verifier confirms them, report surfaces results. Each can be improved independently.
5. **Conservative by default** — when in doubt, show no preview. Coverage grows as we verify, not as we guess.
