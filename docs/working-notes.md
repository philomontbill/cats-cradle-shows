# Working Notes

## Current Status (Feb 20, 2026)

### Email Setup
- info@localsoundcheck.com sends and receives through Gmail
- GoDaddy forwards incoming mail to Gmail

### Artist Outreach — Emails Sent (Feb 19)
All 13 email outreach messages sent via Gmail as info@localsoundcheck.com:

1. Chris Chism — christianchismmusic@gmail.com (Feb 20, CC Back Room)
2. Vacation Manor — ben.rossman@dynamictalent.com (Feb 21, CC Back Room)
3. Briscoe — ryan@tenatoms.com (Feb 22, Cat's Cradle) **RESPONDED — ob@tenatoms.com sent YouTube update**
4. Nuovo Testamento — ricky@swampbooking.com (Feb 23, CC Back Room)
5. Paul McDonald & the Mourning Doves — bross@ellipticmgmt.com (Feb 27, CC Back Room)
6. Al Olender — jmoss@independentartistgroup.com (Mar 3, CC Back Room)
7. Goldie Boutilier — alessandra@highroadtouring.com (Mar 3, Cat's Cradle)
8. Coma Cinema — summertimeinhell@gmail.com (Mar 4, CC Back Room)
9. Nothing — info@mn2s.com (Mar 5, Cat's Cradle)
10. Immortal Technique — peyton@prysmtalentagency.com (Mar 6, CC Back Room) **BOUNCED**
11. The Nude Party — kmosiman@teamwass.com (Mar 6, Cat's Cradle)
12. Dirtwire — booking@dirtwire.net (Mar 7, Cat's Cradle)
13. Rachel Bochner — troy@forgeaheadtouring.com (Mar 8, CC Back Room)

### Instagram DMs Sent (Feb 19)
9 of 11 DMs sent. 2 artists had DMs disabled:
- Peter McPoland (@petermcpoland) — DMs disabled
- Aterciopelados (@aterciopelados) — DMs disabled

### Reddit Post — Ready, Not Yet Posted
- Post saved in outreach/reddit-post-triangle.txt
- Target subreddit: r/triangle
- Best posting time: Tue-Thu, 10am-12pm
- Must be available 2 hours after posting to respond to comments
- Reddit username: NC_Brady (12 karma, 12 contributions, 2 weeks old)

### Spreadsheet Updated
- All outreach statuses logged in Artist List spreadsheet
- Briscoe marked as Responded
- Immortal Technique marked as Email bounced
- Peter McPoland and Aterciopelados marked as DMs disabled

### Decisions Made
- Mission: "Nothing compares to the experience of discovering a fresh talent in the intimacy of a small venue. Local Soundcheck is committed to helping you find great talent and to helping that new talent grow."
- Focus on small and mid-size venues only (no arenas/amphitheaters)
- No hard capacity number — "venues where audiences are likely to encounter artists they don't already know"
- Green field validated — competitive research of 15+ platforms confirmed no one combines venue-first browsing + small venue focus + instant samples
- Prove concept in Triangle before expanding
- Zero budget until proof of concept
- Artist outreach: ask if they see value, not a sales pitch
- Use Gmail as central hub for all Local Soundcheck email
- Reddit: post as NC_Brady (personal account), not a branded account

### Not Yet Started
- Reddit posting (draft ready, need right timing)
- Instagram content strategy
- Response logging / tracking automation

### Key Files
- docs/strategy.md — strategy document
- docs/outreach-templates.md — email and DM templates
- docs/strategy-discussion.txt — raw old conversation (reference only)
- outreach/summary.txt — contact list
- outreach/emails/ — 13 personalized emails
- outreach/instagram_dms.txt — DM targets
- outreach/reddit-post-triangle.txt — ready-to-post Reddit content
- generate_outreach.py — script to regenerate outreach emails

### Accessibility Audit — Completed (Feb 19)
Full WCAG 2.1 AA audit completed. 13 issues found across index.html, styles.css, and app.js.

### WCAG 2.1 AA Remediation — Implemented Feb 20, 2026
All 13 accessibility issues from the Feb 19 audit were implemented and verified on Feb 20, 2026. Files modified: index.html, styles.css, app.js.

**Critical (blocks keyboard/screen reader users) — all resolved:**
1. Show cards keyboard-accessible — `.show-header` and `.opener-name.has-video` have `tabindex="0"`, `role="button"`, `aria-label`, and Enter/Space keydown handlers
2. Skip navigation link — "Skip to shows" link added at top of page, hidden until focused
3. No-preview popup is a proper modal — `role="dialog"`, `aria-modal="true"`, focus trap, Escape key close, `aria-label` on close button, focus returns to triggering element on close
4. YouTube iframes have `title` attribute — `title="YouTube video player for [artist]"`

**Serious — all resolved:**
5. Venue buttons have `aria-pressed` — toggled dynamically on venue switch
6. `aria-live="polite"` region — stats div announces content changes when venue switches
7. Play icon (▶) has `aria-hidden="true"` — parent elements use `aria-label` instead
8. Ticket links have `aria-label` — includes artist name and "(opens in new tab)"
9. "Beyond the Triangle" section moved before `</footer>` — correct document order

**Moderate — all resolved:**
10. Custom `:focus-visible` styles — blue (#5cacee) outline visible on dark background
11. Venue buttons wrapped in `<nav>` — `aria-label="Triangle venues"` and `aria-label="Other cities"`
12. Loading spinner has `role="status"` and `aria-live="polite"`
13. Mobile venue button touch targets increased — padding raised to 10px 16px

**Additional improvement (Feb 20, 2026):**
- YouTube embeds now autoplay when opened (`&autoplay=1`), eliminating an extra click for all users

### Operations Automation — Implemented Feb 20, 2026

Three automation scripts built and integrated into the GitHub Actions nightly scrape workflow:

**1. Scrape monitoring (`monitor_scrapes.py`)**
- Compares show counts to previous run (history stored in `logs/scrape-history.json`)
- Logs every run to `logs/scrape-report.txt`
- Alerts on: zero shows returned, 50%+ drop from previous scrape, JSON parse failures
- Tested locally — all 11 venues healthy on first run

**2. Expanded validation (`validate_shows.py`)**
- Original 5 checks expanded to 12+
- New checks: cancelled/postponed keywords, tour names in artist field, duplicate artists across venues (normalization), missing date/venue/ticket URL, missing images
- Separates warnings (need review) from info (low priority)
- Currently catches 42 warnings and 47 info items across 11 venues

**3. Show expiration (`expire_shows.py`)**
- Marks past shows with `"expired": true` — preserves data for historical reference
- Recalculates `total_shows`, `shows_with_video`, `shows_with_image` to exclude expired
- `app.js` filters expired shows from display
- First run flagged 8 expired shows across 3 venues (boweryballroom, elclub, motorco)

**GitHub Actions workflow updated:**
- All three scripts run after scrapers in nightly workflow
- Creates a GitHub Issue labeled `scrape-alert` when monitor or validation flags issues
- GitHub emails notification automatically (no Gmail app password needed)
- Note: Gmail app password setup was blocked by Google 2FA configuration issue — GitHub Issues used as alternative

**Design decisions (Feb 20):**
- Alerts: log everything, email/notify only on failures
- Thresholds: zero shows OR 50%+ drop triggers alert
- Past shows: flag with `expired: true`, don't delete (preserve historical data)
- Validation: log + notify on warnings, don't block data from going live
- Timing: quick checks after each scrape, plus scripts available for manual runs

### GA4 Event Tracking — Implemented Feb 20, 2026

Custom GA4 events added to app.js. Confirmed working via GA4 Realtime view.

| Event | Parameters | Fires when |
|-------|-----------|------------|
| `venue_switch` | venue_name | User clicks a different venue |
| `sample_play` | artist, venue_name, role (headliner/opener) | User plays a YouTube sample |
| `ticket_click` | artist, venue_name, ticket_url | User clicks Get Tickets |

All events include `venue_name` for per-venue reporting. This enables future venue pitch: "we drove X ticket clicks to your site."

GA4 reporting location: Reports > Business objectives > View user engagement & retention > Events

### Strategy Doc Updated — Feb 20, 2026
- Phase 2 expanded with 6 operational areas that must scale (data quality, YouTube curation, scraper maintenance, venue onboarding, inbound comms, daily checklist)
- Operations backlog added: YouTube auto-matching (needs API key) and daily digest (needs email delivery solution)

### Chrome Extension
- Not connecting to Claude Code this session — troubleshoot next time

### Notes
- YouTube autoplay (`&autoplay=1`) does not work on mobile — browser-level restriction, not a bug
- VS Code Live Preview blocks YouTube embeds (bot detection) — use localhost:8000 for testing video playback
- Google 2FA enabled on Gmail account (Feb 20) but app passwords page was inaccessible — retry later

---

## Session: Feb 21, 2026

### Chrome Browser Connection — Working
- Claude in Chrome MCP extension connected successfully
- Tested on localsoundcheck.com and YouTube
- Connection persists across sessions (extension + MCP config stay installed)
- GA4 access attempted but property not found under philomontbill@gmail.com or info@localsoundcheck.com — likely under soundchecklocal@gmail.com

### Bluegrass Festival Fix
- "Carrboro Bluegrass Festival Presents Bluegrass In The Backroom" was being treated as an artist name
- Corrected: artist = "Six More Miles", opener = "North State Grass", festival name moved to notice field
- Added `show_overrides` to `scrapers/overrides.json` — scraper now applies name corrections before YouTube matching
- North State Grass video set to `w54lLXcuv9g` (user-provided)
- Six More Miles has no video yet (NC bluegrass band, members from Watchhouse, Jim Lauderdale, Chatham Rabbits)

### Project Reorganization
- Created `scripts/` directory — moved expire_shows.py, monitor_scrapes.py, validate_shows.py out of root
- Updated GitHub Actions workflow and CLAUDE.md references
- Root is now cleaner: website files at root, operations scripts in scripts/

### YouTube Match Accuracy — Round 1 (Greenlit & Executed)

**Problem**: Product value depends on right video for every band. Wrong video is worse than no video. No way to measure accuracy or systematically improve it.

**Stretch goal documented**: Proprietary matching algorithm as competitive moat (see strategy.md)

**Baseline audit completed**:
- Built `qa/audit_accuracy.py` — checks every youtube_id against actual video title/channel via oEmbed
- Result: **77.7% accuracy** across 337 videos (262 high confidence, 24 medium, 51 low)
- Best venues: The Social (100%), Cat's Cradle (93%), Mohawk (89%)
- Worst venues: Pinhook (58%), Local 506 (63%), Bowery Ballroom (67%)
- Common failure patterns: multi-artist shows, event names as artists, common/short band names

**El Club removed from site** — only 11% video coverage (2 of 18 shows). Data and scraper preserved for future.

**YouTube Data API integration built**:
- API key from Google Cloud Console (project: My No Code Project 11164)
- Key stored in `.env` (gitignored) and GitHub secret `YOUTUBE_API_KEY`
- `base_scraper.py` rewritten with API-based search + confidence scoring
- Two signals: channel name match (strongest) + Music category filter
- Three tiers: accept (>=70), flag (40-69), skip (<40)
- Single-word artist names handled specially to prevent false positives (e.g., "Nothing" no longer matches Whitney Houston)
- All matches logged to `qa/match_log.json`
- Falls back to scraping if no API key available
- Nightly workflow updated to pass API key as environment variable
- First API-powered scrape runs tonight at 11 PM ET

### QA Directory Structure
- `qa/` — top-level directory for quality assurance
- `qa/audits/` — timestamped audit results (baseline: 2026-02-21)
- `qa/corrections.json` — manual correction log (training data)
- `qa/audit_accuracy.py` — audit script
- `qa/match_log.json` — generated by scraper, logs every YouTube match decision
- `qa/README.md` — documents purpose and structure

### Key Files (updated)
- docs/strategy.md — strategy document (YouTube accuracy plan added)
- docs/working-notes.md — this file
- docs/outreach-templates.md — email and DM templates
- docs/strategy-discussion.txt — raw old conversation (reference only)
- scripts/monitor_scrapes.py — scrape health monitoring
- scripts/validate_shows.py — show data validation
- scripts/expire_shows.py — past show expiration
- scrapers/base_scraper.py — scraper base class (now with API matching + confidence scoring)
- scrapers/overrides.json — manual YouTube overrides + show-level name corrections
- qa/audit_accuracy.py — YouTube match accuracy audit
- qa/corrections.json — manual correction log
- qa/match_log.json — auto-generated match decisions
- qa/audits/ — timestamped audit snapshots
- logs/scrape-history.json — previous scrape counts
- logs/scrape-report.txt — scrape monitoring log
- outreach/ — outreach emails, DMs, Reddit post

### YouTube Match Accuracy — Round 1 Complete (Feb 21, 2026)

**Accuracy progression:**

| Run | Accuracy | High | Low | No Video | What changed |
|-----|----------|------|-----|----------|-------------|
| Baseline (pre-API) | 77.7% | 262 | 51 | — | oEmbed audit only |
| First API run | 94.7% | 288 | 12 | 57 | YouTube Data API + confidence scoring |
| After name cleaning | 87.6% | 298 | 24 | 21 | Cleaned names found videos for 36 previously-missing entries (most scored low) |
| + Event keywords | 89.8% | 299 | 21 | 28 | Null out event names |
| + Final round | 90.3% | 298 | 19 | 31 | More event patterns, overrides |

Note: accuracy dropped from 94.7% to 87.6% because name cleaning caused the scraper to find YouTube videos for entries that previously had none — mostly event names and multi-band bills that matched wrong videos. The denominator grew faster than the numerator. On the entries that had videos in both runs, accuracy improved.

**What was fixed in Round 1:**
- YouTube Data API integration with confidence scoring (replaced scraping)
- Smart search filtering to preserve API quota (reuse high-confidence matches)
- Audit scorer: compact matching (DRUG DEALER/Drugdealer), slash normalization, VEVO/Topic channel recognition
- Scraper name cleaning: strip tour suffixes after colons and dashes, split multi-artist on comma/" / "/"w/", strip "Presents" suffix, strip "feat." suffix
- Event name detection: Cabaret, Burlesque, Prom, Quizzo, Showcase, DJs:, GrrrlBands, Honoring, Tribute Band, etc.
- Overrides added: MODEL / ACTRIZ, DRUG DEALER

**19 remaining low-confidence entries (punch list for Round 2):**

*Multi-artist fields using "and" as separator (Local 506 pattern):*
1. Buck Swope and Green Room — Local 506 opener
2. Small Doses and Chiroptera — Local 506 opener
3. Snowblinder and Dead Halos — Local 506 opener
4. Julian Calendar and Sonic Blooms — Local 506 opener
5. Let's Sabbath and One After 919 — Local 506 opener

*Single-word/generic band names:*
6. Heated (x2) — Motorco headliner, matches H.E.A.T instead of the band Heated
7. Nudey, DJ Sipper — Bowery opener, multi-artist

*Multi-artist fields (comma-separated, first name too obscure):*
8. The Rikkies & SUM SUN w/ So Impartial — Bowery headliner, "Rikkies" too obscure
9. Ben Milk, Brady Dorrington, ChatChat — Bowery headliner, "Ben Milk" matches MILK BAND
10. Harmony Dawn, Meera Dahlmann, Lizzy Campbell — Bowery headliner

*Fan channels / wrong channel name:*
11. Kevin Devine: 20 Years... — Bowery, correct video but fan channel "KevinDevineVideo" doesn't match scorer
12. Siamese – US Headline Tour 2026 — Local 506, correct video but channel "Alternative Music Leader"
13. Robert Morton 'Self Loathing...' — Local 506, wrong video (matched "Unii" instead)

*Event names not yet caught:*
14. Honoring JR feat. Audiohum... — Elevation 27 (should be null, "Honoring" keyword was added but may not have applied in this run)
15. Last Fair Deal: A Grateful Dead Tribute Band... — Elevation 27 (tribute band, valid name, bad match)
16. The Cast Of Beatlemania — Elevation 27 (tribute act, video is correct but scorer doesn't recognize it)
17. Hex Files / Little Chair / Future Fix... — Pinhook (first band "Hex Files" matched wrong video)

*Slash-separated with partially correct match:*
18. SADBOY PROLIFIC / JOMIE — Motorco opener, video is SadBoyProlific (correct for first artist) but scorer can't tell

**13 medium-confidence entries (may be correct, need manual verification):**
- BEAUTY SCHOOL DROPOUT (Bowery) — video is correct, BSDVEVO channel
- Arianna Chetram (Bowery) — video is correct, fan channel
- Slow Teeth (Cat's Cradle) — video appears correct
- Advance Base (Pinhook) — video is correct
- Invisible Cities (Pinhook) — video appears correct
- Cootie Catcher (Pinhook) — video is correct, Carpark Records channel
- JULIA. Fish in the Percolator (Kings) — needs checking
- Cast of Beatlemania (Elevation 27) — correct video, low score
- 5 others at Elevation 27, Kings, Local 506 — mixed, some event names

### Video Disclaimer — Implemented Feb 21, 2026

Added a disclaimer that appears above the YouTube player every time a user clicks to preview an artist. Two lines:
- **Red bold**: "IMPORTANT! Always verify the artist before purchasing tickets." ("IMPORTANT!" is underlined)
- **Muted gray**: Explains we're a young company, invites users to report mismatches to info@localsoundcheck.com

Purpose: protect users from acting on a wrong video match, and turn users into a feedback loop for accuracy improvement. Styled to be prominent without blocking the video experience.

Files modified: app.js (disclaimer element inserted above player wrapper), styles.css (`.video-disclaimer`, `.disclaimer-warning`, `.disclaimer-important`, `.disclaimer-body`)

---

## Session: Feb 21, 2026 (continued)

### Accuracy Round 1 — Completed

Added accuracy audit to the nightly GitHub Actions workflow. Ran 4 manual workflow runs to iterate on improvements.

**Audit scorer fixes (qa/audit_accuracy.py):**
- Added `compact()` function for collapsed-name matching (DRUG DEALER vs Drugdealer)
- Slash normalization in `normalize()` (MODEL / ACTRIZ)
- VEVO and "- Topic" channel recognition as strong signals

**Scraper name cleaning improvements (scrapers/base_scraper.py):**
- Strip "Presents" as suffix (keeps band name: "Beauty School Dropout Presents: ..." → "Beauty School Dropout")
- Strip tour/event info after colons ("Kevin Devine: 20 Years..." → "Kevin Devine")
- Split multi-artist on comma, " / " (space-slash-space), and "w/"
- No-space slash preserved as single band name (Model/Actriz stays intact)
- Strip "US Tour", "Album Release", "feat." suffixes without dash prefix
- Event name detection expanded: Prom, Quizzo, Blowout, Graduation, Takeover, Honoring, Tribute Band, GrrrlBands, DJs:, Songwriters Show, Blends With Friends, Party Iconic, "It's A 2000s Party"
- Check event keywords on original name before colon-stripping

**Overrides added:** MODEL / ACTRIZ (`37ptdYkJ1d0`), DRUG DEALER (`cHY-rgmjEq4`)

**Accuracy progression:** 77.7% → 94.7% → 87.6% → 89.8% → 90.3%
- The drop from 94.7% to 87.6% was a denominator problem — name cleaning found videos for 36 previously-missing entries that mostly scored low (event names, multi-band bills)
- On entries that had videos in both runs, accuracy improved

### Video Disclaimer — In Progress

Built and tested a disclaimer above the YouTube player. Iterated through several versions:
1. Small muted text below video — too subtle
2. Red bold "Always verify..." above video — more prominent but too scary
3. "IMPORTANT!" underlined + red bold — even scarier
4. Softer mission-focused version — better tone but needs more work

Removed from live site for now. CSS classes remain in styles.css for easy re-addition. Key decisions still needed:
- Balance between protecting users and not scaring them away
- Tone should invite collaboration, not warn of danger
- Should communicate mission (emerging talent discovery) while encouraging double-checking

### Peter McPoland Video — Fixed

Was serving a YouTube Short (`PcqWYLat8mc` — "Big Lucky album out tonight"). Smart filtering kept reusing it because it scored 85 (high confidence — correct channel, just wrong type of video). Added manual override to `x6nNVUSK-3Y` ("What Do You Do To Me" Official Video from the Big Lucky album). Lesson: the audit scorer can't distinguish between a proper music video and a Short from the same artist.

### Next Steps
- Finalize video disclaimer wording and re-add to site
- Multi-act feature: show individual band names with separate video/no-preview indicators for comma/slash-separated opener fields (task #13)
- Round 2 accuracy: address the 19 low-confidence punch list (see above)
- Consider "and" as band separator for Local 506 (risky — could break "Florence and the Machine" type names)
- Manual verification pass on the 13 medium-confidence entries
- Round 2 planning: additional scoring signals based on Round 1 match log data

---

## Session: Feb 22, 2026

### Briscoe Video Override
- Briscoe plays tonight at Cat's Cradle. Artist's team (ob@tenatoms.com) provided preferred video.
- Added override: `j7WBQW4AIMc` in `scrapers/overrides.json` and updated `data/shows-catscradle.json`
- Previous video `yEUrcsny2XA` replaced — override ensures nightly scraper preserves their choice

### Rhineland Opener — Verified Correct
- Checked the Feb 21 opener Rhineland (Cat's Cradle Back Room) after user concern about wrong band
- Video served: `0iYh8KrzFk8` — "Rhineland - Burning (Official Video)" from channel "Rhineland" (414 subs)
- Confirmed via rhineland.band website: band is from **Lynchburg, Virginia** — matches user's description
- Audit scored 95 confidence (high) — correct match confirmed

### Chrome Extension — Dual Profile Setup
- Claude in Chrome extension installed on both Philomont (dev) and Soundcheck (analytics) Chrome profiles
- `switch_browser` tool works to hop between profiles when both extensions are active
- Tab group limitation: closing the last non-Claude tab in a group deletes the group and disconnects

### GA4 Analytics Review (Last 28 Days: Jan 25 - Feb 21)

**Overview:**
- 61 active users (all new)
- 535 total events
- 186 page views
- 1m 55s average engagement
- 70.7% bounce rate

**Traffic sources:**
- 56 direct, 4 facebook.com/referral, 1 Instagram/social

**Top cities:** Ashburn (6, likely VPN/data center), Charlotte (5), Aspen (4), Council Bluffs (3), Warsaw (3), Dallas (2), High Point (2)

**Custom events firing:**
- `sample_play`: 23 events by 3 users (7.67 plays per user — strong engagement signal)
- `venue_switch` and `ticket_click`: not yet recorded (either no usage or events added recently)

### GA4 Custom Dimensions — Registered Feb 22, 2026

Custom event parameters were not visible in GA4 reports because they weren't registered as custom dimensions. Created 4 dimensions:

| Dimension | Event Parameter | Scope | Description |
|-----------|----------------|-------|-------------|
| Artist | `artist` | Event | Artist name from sample_play and ticket_click events |
| Role | `role` | Event | Artist role (headliner or opener) from sample_play events |
| Ticket URL | `ticket_url` | Event | Ticket purchase URL from ticket_click events |
| Venue Name | `venue_name` | Event | Venue name from sample_play, venue_switch, and ticket_click events |

**Note:** GA4 does not allow editing event parameters after creation. Two dimensions (Role, Venue Name) were initially created with wrong casing (capital R, capital V). Had to archive and recreate with correct lowercase parameters. GA4 parameters are case-sensitive — must match exactly what the code sends.

Data populates in standard reports within 24-48 hours; Realtime reports show immediately.

**GA4 recommendation noted:** Link Search Console property (sc-domain:localsoundcheck.com) to see which search queries drive traffic. 1-minute setup — do this next session.

### Weekly Analytics Report — Built & Deployed Feb 22, 2026

Automated weekly report that pulls GA4 data and posts as a GitHub Issue every Monday at 6 AM ET.

**Setup completed:**
1. Google Analytics Data API enabled in Google Cloud Console (project: My First Project / polar-pilot-488221-v0)
2. Service account `soundcheck-analytics` created with JSON key
3. Service account added as Viewer on GA4 property (ID: 522912109)
4. GitHub Secrets set: `GA4_PROPERTY_ID`, `GA4_SERVICE_ACCOUNT`

**Report sections:**
- Overview: users, new vs returning, page views, avg engagement, events (with week-over-week comparison)
- Venue Activity: per-venue breakdown of users, views, plays, ticket clicks, top artist
- User Origins: top 10 cities by users
- Traffic Sources: source/medium breakdown
- Top Artists Played: top 10 artists with venue and role
- Device Breakdown: mobile/desktop/tablet split

**First test run (Feb 15-21 data):**
- 28 users (+65% vs prior week), 104 page views (+225%), 3m 33s avg engagement
- Top traffic: direct (23), Facebook (4), Google organic (1), Instagram (1)
- Top cities: Ashburn VA (5), Charlotte NC (2), High Point NC (2)
- 60.7% desktop, 35.7% mobile, 3.6% tablet
- Venue and artist sections empty as expected — custom dimensions just registered today

**Files created:**
- `scripts/weekly_report.py` — main report script (GA4 Data API queries, text table formatting, GitHub Issue posting)
- `.github/workflows/weekly-report.yml` — Monday 10 AM UTC cron + manual trigger
- `requirements.txt` — google-analytics-data, google-auth

**On-demand usage:**
```bash
python scripts/weekly_report.py                      # Default 7-day → GitHub Issue
python scripts/weekly_report.py --days 30            # Last 30 days
python scripts/weekly_report.py --venue catscradle   # Filter to one venue
python scripts/weekly_report.py --artist "Briscoe"   # Filter to one artist
python scripts/weekly_report.py --output report.txt  # Write to file instead
```

**Note:** Venue and artist breakdowns depend on custom dimensions registered today. First meaningful data for those sections will be the week of Feb 23 - Mar 1.

### Next Steps
- Finalize video disclaimer wording and re-add to site
- Multi-act feature (task #13)
- Round 2 accuracy: address 19 low-confidence punch list
- Manual verification pass on 13 medium-confidence entries
- Link Google Search Console to GA4
- Check GA4 custom dimensions are populating after 24-48 hours
- Verify first automated weekly report posts Monday Mar 2

---

## Session: Feb 23, 2026

### Critical Bug Fix — API Scoring Never Worked

Discovered that `_search_youtube_api()` in `base_scraper.py` had a variable name bug: lines 278 and 304 referenced `clean_name` instead of `artist_name`. This variable was never defined in that function. Every API search:
1. Made the YouTube API call (used quota)
2. Crashed on `NameError` when trying to score results
3. Got caught by a broad `except Exception`
4. Silently fell back to scraping YouTube HTML with zero confidence checks

**The entire confidence scoring system (accept/flag/skip tiers) never executed for API searches.** All video matches came through the web scraping fallback, which just takes the first YouTube result with no scoring. This explains many wrong matches.

Fixed: two-line change, `clean_name` → `artist_name` on lines 278 and 304. Tonight's nightly scrape will be the first time confidence scoring actually runs.

### Video Matching Logic — Full Design Review

Walked through all four phases of the video matching pipeline documented in `qa/video-matching-logic.md`:

**Phase 1 (Schedule Updates):** How the scraper decides what to search. Override → verified → unverified flow. Discussed Rivalry Night edge case, venue placeholder image detection, multi-act openers (deferred).

**Phase 2 (YouTube Candidate Search):** Name cleaning, event keyword detection, API search with Music category filter, confidence scoring. Found and fixed the `clean_name` bug during this review.

**Phase 3 (Verifier — Multi-Step Validation):** New verification layer. Decisions locked in:
- View count cap: **5 million** (single universal threshold, all venues same tier)
- Topic channel exception: skip view count if "{ArtistName} - Topic" matches
- Subscriber count: modifier only, not a hard threshold. 2M+ on non-matching channel = red flag
- Upload date: flag if 15+ years old with no channel match (not a hard reject alone)
- Venue placeholder image: flag if show uses venue default artwork (e.g., cradlevenue.png)

**Phase 4 (Daily Video Report):** Report format with four sections — Tonight's Changes, New Verified Videos, Rejected Candidates, No Preview Queue. Posted as GitHub Issue with clickable YouTube URLs.

### Video Verifier — Built and Deployed

New script `scripts/verify_videos.py` implements Phase 3 of the pipeline.

**First run results (all venues, Feb 23):**
- 285 videos verified and locked in
- 40 wrong matches caught and removed from show data
- ~650 API quota units (6.5% of daily budget)

**Notable catches:**
- Bryce Vine (98.7M views), Alien Ant Farm (382M, "Smooth Criminal"), yung kai (247M)
- Oof Fighters matched actual Foo Fighters channel (4.2M subs) — tribute band at wrong video
- KEXP, NPR Music, Metallica, Epitaph Records channels caught by subscriber threshold
- Rivalry Night caught by venue placeholder image before any API call

**False rejections to investigate:** Aterciopelados (42M, real band), Gogol Bordello (14M, real band), POWFU (8.2M, internet-famous), Caroline Jones (9.5M). These are real artists playing these venues whose legitimate videos exceed the 5M cap — need manual overrides.

**Files created:**
- `scripts/verify_videos.py` — verifier script (view count, channel analysis, Topic detection, upload date, venue placeholder)
- `qa/video_states.json` — verification state for 324 artists (285 verified, 39 rejected)
- `qa/verification-log.md` — running operational log of verification runs, findings, calibration decisions

**Nightly workflow updated:**
- Added "Verify video assignments" step to `.github/workflows/scrape.yml`
- Runs after validate, before accuracy audit
- Posts daily video report as GitHub Issue (label: `daily-video-report`)
- `qa/video_states.json` included in nightly commit

### QA Documentation Structure

- `qa/video-matching-logic.md` — **design spec** (rules, thresholds, decision tree, reasoning)
- `qa/verification-log.md` — **operational log** (run results, findings, calibration history)
- `qa/video_states.json` — **state data** (verified/rejected status per artist, auto-updated)
- `qa/audits/` — timestamped accuracy audit snapshots (unchanged)

### Next Steps
- Review false rejections: Aterciopelados, Gogol Bordello, POWFU, Caroline Jones — add overrides if legitimate
- Monitor first automated verifier run (tonight 11 PM ET)
- Check daily video report GitHub Issue arrives tomorrow morning
- Finalize video disclaimer wording and re-add to site
- Multi-act feature (task #13)
- Link Google Search Console to GA4
- Verify first automated weekly report posts Monday Mar 2
