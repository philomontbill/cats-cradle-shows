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
12. **Generic venue image check** (free, no API call) — if the show's image URL matches a known venue placeholder (e.g., Cat's Cradle uses `cradlevenue.png`), treat this as a strong signal the entry may be an event rather than a band. Each venue has at most one placeholder URL to check against. Note: occasionally a real band may not have artwork uploaded yet, so this is a rejection signal in the verifier, not a hard block in the scraper. If a real band gets caught by this, it shows up in the daily report and can be overridden.
13. For each unverified candidate, pull video metadata from YouTube `videos` endpoint (1 quota unit):
    - **View count check** — reject if views exceed **5 million**. All our venues are small indie rooms (100-750 capacity). Bands playing these rooms typically have videos in the 10K-2M range. 5M catches all famous-song collisions (Hank Williams, Whitney Houston, Beyonce) while leaving headroom for legit bands with a breakout hit. Single universal threshold — no per-venue variation needed since all venues are the same tier. Can tighten later based on daily report data.
    - **Topic channel exception** — if the video is from a YouTube auto-generated "{ArtistName} - Topic" channel and the artist name matches, **skip the view count check**. Topic channels aggregate YouTube Music streaming plays, so a small indie band can have 500K+ plays. The Topic designation + artist name match is one of the strongest possible confirmations (YouTube itself recognized the artist).
    - **Upload date check** — flag if video age doesn't fit a current touring artist. A video from 2005 for a band playing next week warrants suspicion. Not a hard reject on its own — bands tour old catalogs. But combined with other weak signals, it tips toward rejection.
14. Pull channel info from YouTube `channels` endpoint (1 quota unit):
    - **Channel name match** — does the channel name relate to the artist? This was already scored in Phase 2, but the verifier confirms it with the actual channel data (not just the search snippet).
    - **Channel type** — is this the artist's own channel, a Topic channel, or a compilation/covers/lyric channel? Own channel or Topic = positive. Compilation or covers = negative.
    - **Subscriber count as modifier (not a threshold)** — subscriber count is too noisy for hard cutoffs (one indie band has 50K subs, another has 400). Instead, use it to modify confidence: non-matching channel + 2M subscribers = strong red flag (wrong channel). Matching channel + 200 subscribers = fine (small band, own channel). Never rejects on its own.
15. Apply confidence threshold with all signals combined:
    - **Pass all checks** → promote to "verified," assign youtube_id, video goes live
    - **Fail any check** → reject, assign no-preview, log the reason
    - Design choice: "fail any = reject" is deliberately conservative. If this proves too aggressive, we loosen specific checks based on what the daily report shows us.
16. Rejected candidates and their reasons are preserved for the daily report

### Phase 4: Daily Video Report
17. Generate report covering:
    - **Tonight's Changes** — summary counts (new shows, verified, rejected, expired)
    - **New Verified Videos** — what passed and went live (with confidence and check results)
    - **Rejected Candidates** — what the scraper found but the verifier refused, with specific reasons (this is how we learn and calibrate)
    - **No Preview Queue** — full running list of all artists currently showing the popup, with status (override, rejected, no results, etc.)
18. Post as GitHub Issue (triggers email notification)

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
Artist           | Venue              | Date     | Video                                        | Confidence
-----------------+--------------------+----------+----------------------------------------------+-----------
Waxahatchee      | Cat's Cradle       | Mar 15   | youtube.com/watch?v=dK3qT5r0cMc              | 95 (channel match)
Slow Teeth       | CC Back Room       | Mar 18   | youtube.com/watch?v=a8Fk29xL4pQ              | 88 (channel + low views)

REJECTED CANDIDATES
Artist           | Venue              | Date     | Candidate                                    | Reason
-----------------+--------------------+----------+----------------------------------------------+---------------------------
Some Band        | Local 506          | Mar 16   | youtube.com/watch?v=82fR-6N0JQc              | 12M views (cap: 5M)

NO PREVIEW QUEUE (7 total)
Artist           | Venue              | Date     | Status
-----------------+--------------------+----------+---------------------------
Six More Miles   | CC Back Room       | Feb 25   | Override: no video
Some Band        | Local 506          | Mar 16   | Rejected: view count (12M, cap 5M)
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

## Planned Enhancement: Multi-Act Openers

Currently each show has a single `opener` string and one `opener_youtube_id`. The scraper splits on comma, takes the first name, and that single video represents all openers. Example: "Full Body 2, Cryogeyser, VMO a.k.a. Violent Magic Orchestra" → only Full Body 2 gets a video lookup.

The plan is to change the data model so each opener is a separate entry with its own name and video:

```json
"openers": [
    {"name": "Full Body 2", "youtube_id": "xe7rEv5UgRA"},
    {"name": "Cryogeyser", "youtube_id": null},
    {"name": "VMO a.k.a. Violent Magic Orchestra", "youtube_id": null}
]
```

Each opener gets their own play button on the site and goes through the same verification pipeline. Most openers will get no-preview and that's fine — openers at small venues are often too obscure for YouTube matches.

This is a significant change touching the data format, every scraper, the verifier, and app.js. It will be implemented after the verifier pipeline is in place, building on top of it rather than alongside it.

Also applies to the Rivalry Night pattern (Mar 5, Cat's Cradle Back Room) where openers have school affiliations in parentheses: "Dialtone (Duke), Red Kanoo (UNC)". The parenthetical stripping already in name cleaning would handle the "(Duke)" and "(UNC)" tags.

## Design Principles

1. **No video is better than wrong video** — the no-preview popup is an acceptable user experience. A wrong video is not.
2. **Confirmed videos are immutable** — once verified or overridden, the nightly scrape cannot change them.
3. **The daily report is a feedback loop** — rejected candidates teach us where the rules are too tight. Wrong matches that slip through teach us where they're too loose.
4. **Separation of concerns** — scraper finds candidates, verifier confirms them, report surfaces results. Each can be improved independently.
5. **Conservative by default** — when in doubt, show no preview. Coverage grows as we verify, not as we guess.
