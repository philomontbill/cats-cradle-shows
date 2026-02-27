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

### Spot Check — Verifier Results on Live Site

After the verifier ran and Vercel deployed, manually checked localsoundcheck.com:

| Show | Venue | Expected | Actual | Result |
|------|-------|----------|--------|--------|
| Nuovo Testamento | Cat's Cradle | Video plays | Correct video | Pass |
| Six More Miles | Cat's Cradle | No preview | No preview popup | Pass |
| Rivalry Night | Cat's Cradle | No preview (rejected) | No preview popup | Pass |
| Cut Worms | Motorco | Video plays | Correct video | Pass |
| POWFU | Motorco | No preview (rejected) | No preview popup | Pass |
| Heated | Motorco | Should be no preview | Wrong video (H.E.A.T) | **Fixed** |
| Colony House | Mohawk | Video plays | Correct video | Pass |
| Oof Fighters | Mohawk | No preview (rejected) | No preview popup | Pass |
| Gogol Bordello | Mohawk | No preview (rejected) | No preview popup | Pass |

**Heated fix:** Single-word name collision — "Heated" (local band at Motorco) matched H.E.A.T (Swedish rock band). Verifier missed it because views were under 5M and channel name fuzzy-matched. Added null override for both casings. Single-word names remain the hardest category for automated matching.

### Daily Video Report — First Issue Posted

Ran verifier a second time after spot check fixes. Posted as GitHub Issue #10. Second run used 0 API units (everything already verified/overridden from first run). Report correctly shows Heated as "No video from scraper" after override.

Daily report will now post automatically every night after the scrape.

### Next Steps
- Review false rejections: Aterciopelados, Gogol Bordello, POWFU, Caroline Jones — add overrides if legitimate
- Monitor first automated verifier run (tonight 11 PM ET)
- Multi-act feature: show individual band names with separate video/no-preview indicators (discussed, not started)
- Finalize video disclaimer wording and re-add to site
- Reddit post ready but not yet posted (outreach/reddit-post-triangle.txt)
- Link Google Search Console to GA4
- Verify first automated weekly report posts Monday Mar 2

---

## Session: Feb 23, 2026 (continued)

### DNS Cleanup — Completed
- Checked DNS records for localsoundcheck.com via Vercel dashboard
- Found 5 stale Microsoft 365 / GoDaddy records (MX, 2 CNAMEs, 2 TXTs) from old email setup
- Deleted all 5 — no longer needed since info@localsoundcheck.com is inactive
- Remaining: 2 ALIAS records (Vercel hosting) + 1 CAA record (Let's Encrypt SSL)

### GitHub Notifications — Configured
- Repo was not being "Watched" — enabled Watch for all activity
- Added soundchecklocal@gmail.com as verified email on GitHub account
- Set as notification email for repository issues (daily video reports, weekly analytics, scrape alerts)

### Manual Video Overrides — 20 Artists Reviewed & Applied

Reviewed all 38 videos rejected by the verifier. Categorized as correct rejections (events, wrong matches, view count too high for wrong artist) vs false rejections (legitimate artists whose real videos tripped thresholds).

**Stepwise verification process established** for manual review:
1. Navigate to the YouTube video in Chrome, take screenshot
2. State video details (channel, subscribers, views, upload date)
3. Give recommendation (accept/reject) with reasoning
4. Wait for user OK or reject
5. Log any disagreements for calibration

**Criteria used for accept/reject decisions:**

*Identity Verification:*
1. **Channel ownership** — Is the video on the artist's own channel or a recognized label? (e.g., Nuclear Blast for Burning Witches, Epitaph for Death Lens, Secret City Records for Barr Brothers, Innovative Leisure for Mint Field)
2. **Channel verification** — Does the channel have a YouTube verification checkmark or Vevo badge?
3. **Subscriber count** — Higher count = stronger signal the channel is legitimate and established
4. **Artist name match** — Does the channel name and/or video title match the artist name from our show data?

*Video Quality Signals:*
5. **View count** — Under the 5M cap, but also reasonable for the artist's tier (42M for Aterciopelados makes sense for a Latin Grammy winner; 874K for Dream, Ivory makes sense for indie)
6. **Video type** — Official music video, lyric video, live performance, or static artwork? All acceptable, but official MV is strongest
7. **Upload recency** — Not a dealbreaker, but newer uploads suggest active artist

*Rejection Signals:*
8. **Event vs. artist** — Is the name actually a band, or an event/party name? (DISCO, ALWAYS = Harry Styles dance night, not a band)
9. **Common word collision** — Single-word or generic names that match the wrong artist entirely (Heated → H.E.A.T)
10. **Label/distributor mismatch** — Video posted by a channel with no connection to the artist

**These criteria should inform automation improvements.** Several could be encoded into the verifier:
- Channel verification badge / Vevo badge = strong trust signal (could override view count cap)
- Known label channels (Nuclear Blast, Epitaph, Secret City, etc.) = trusted sources
- Artist name ↔ channel name match + high subscriber count = likely correct even with high views
- Event keyword detection already exists but could be expanded based on patterns seen here

**20 overrides added across 3 batches:**

| Artist | Video ID | Channel | Why Override |
|--------|----------|---------|-------------|
| ALESANA | ntRXE7oLVf8 | Alesana (verified) | Own channel, views under cap |
| SKIZZY MARS | U7svgD2yPig | Skizzy Mars | Own channel, views under cap |
| The Band Of Heathens | KLxHd3XCrTw | BandOfHeathens | Own channel |
| Kxllswxtch | uCEGV2weoPs | Kxllswxtch | Own channel |
| LETDOWN | PsKg8dEWWco | LETDOWN (verified) | Own channel, Epitaph Records |
| Love Letter | 3dbvSe8BtoA | Love Letter (verified) | Own channel, punk band |
| Burning Witches | 1OCmwMFKDlE | Nuclear Blast Records | Major metal label, 3M views |
| Death Lens | yDY3QCkc9n0 | Epitaph Records | Major punk label, 20K views |
| Buffalo Nichols | IUJj6nu1guY | Buffalo Nichols | Own channel, 148K views |
| The Barr Brothers | 1JU4T9iqNTo | Secret City Records | Indie label, 910K views |
| Mint Field | -E4HZt8u5QI | Innovative Leisure | Indie label, 64K views |
| Lil Texas | gygm4c5z3d0 | Lil Texas | Own channel, static artwork |
| DISCO, ALWAYS | null | — | Event (Harry Styles night), not a band |
| Aterciopelados | sUlsTs2ljaE | Aterciopelados (verified) | Own channel, Latin Grammy winners, 42M views legit |
| Gogol Bordello | SkkIwO_X4i4 | SideOneDummy | Label channel, 11M views, iconic band |
| POWFU | KVg-UTZrpgo | Powfu | Own channel, 404K views |
| Caroline Jones | yy0S5UN1X10 | Caroline Jones | Own channel, 171K views |
| Bryce Vine | o_tUi4U1pG4 | Bryce Vine | Own channel, 94K views |
| yung kai | iQmvTvGJfQs | yung kai | Own channel, 1.3M views |
| Dream, Ivory | 99PzeVVVCn8 | Dream, Ivory (Vevo) | Own channel, 874K views |

3 artists had expired shows (Buffalo Nichols, Love Letter, Death Lens) — overrides.json only, no show data update needed.

### Next Steps
- Monitor first automated verifier run (tonight 11 PM ET)
- Remaining video quality: 19 low-confidence entries, 13 medium-confidence entries
- El Club scraper investigation (18 shows with no video)
- Consider encoding manual review criteria into verifier (label allowlist, verification badge detection, artist-tier-aware view caps)
- Multi-act feature (discussed, not started)
- Finalize video disclaimer wording
- Reddit post (outreach/reddit-post-triangle.txt)
- Link Google Search Console to GA4 (**done** — see below)
- Verify first automated weekly report Monday Mar 2

---

## Session: Feb 23, 2026 (session 3)

### GA4 Custom Dimensions — Confirmed Working
- Tested custom dimensions by visiting localsoundcheck.com on phone while watching GA4 Realtime
- Realtime showed sample_play events with correct artist parameter values: "Nuovo Testamento" (2 plays), "North State Grass" (1 play)
- All 4 dimensions (artist, role, venue_name, ticket_url) confirmed populating correctly
- Note: Soundcheck Chrome profile had 503 errors on google-analytics.com/g/collect — browser-specific issue, phone traffic worked fine

### Google Search Console — Linked to GA4
- Linked localsoundcheck.com Search Console property to GA4 via Admin > Product Links > Search Console Links
- Selected Domain property (sc-domain:localsoundcheck.com) and Local web stream
- Link created successfully — search query data will appear in GA4 reports

### Spotify API Integration — Planned, Blocked on Premium
- Discussed Spotify vs Bandsintown for video verification quality improvement
- Recommendation: Spotify first (artist disambiguation, track name cross-referencing, popularity scores)
- Bandsintown better for show data validation but more restrictive API
- Spotify requires Premium account for Development Mode API access (Feb 2026 change)
- **Blocker: user needs to upgrade to Spotify Premium before proceeding**
- Full implementation plan saved in `.claude/plans/fuzzy-stargazing-starfish.md`
- Plan covers: app setup, `scripts/spotify_enrich.py`, caching, workflow integration, phased rollout

### Next Steps
- ~~**Blocked**: Spotify integration — waiting on Premium upgrade~~ **Unblocked — see Feb 24 session**
- Monitor first automated verifier run (tonight 11 PM ET)
- Remaining video quality: 19 low-confidence entries, 13 medium-confidence entries
- El Club scraper investigation (18 shows with no video)
- Multi-act feature (discussed, not started)
- Finalize video disclaimer wording
- Reddit post (outreach/reddit-post-triangle.txt)
- Verify first automated weekly report Monday Mar 2

---

## Session: Feb 24, 2026 — Spotify + Manual Video Review

### Spotify API Integration — Phase 1 Complete

Spotify Premium upgraded, app created on developer.spotify.com, credentials stored in `.env` and ready for GitHub Secrets.

**New script: `scripts/spotify_enrich.py`**
- Auth: Client Credentials flow (no user login needed)
- Searches Spotify for each artist, picks best match using name similarity scoring
- Fetches top 10 tracks for matched artists
- Caches results in `qa/spotify_cache.json` with 30-day TTL
- CLI: `--artist "Name"` (single lookup), `--dry-run`, `--force` (bypass cache)

**First full run results (352 unique artists):**
- 212 found on Spotify, 140 not found
- 210 strong matches (exact or close)
- Event names correctly rejected (DURHAM MARDI GRAS, COMMON WOMAN CABARET, etc.)
- Multi-artist bills correctly rejected (comma-separated, "and" separated)

**Name similarity scoring refined during testing:**
- Length ratio check prevents short-word containment false positives ("Common" no longer matches "COMMON WOMAN CABARET 2026")
- Multi-word names (3+ words) require higher threshold (0.7 vs 0.5) to match
- Three confidence tiers: exact (1.0), close (0.8+), partial (0.5+)

**Edge cases noted (low impact for Phase 1):**
- `DISCO, ALWAYS` → "Always Discover" (partial, pop=0, 3 followers) — weak false positive
- `@ Kings` → "KINGS" — "@" stripped by normalization
- `An Evening` / `An Evening With` → matched unrelated bands — truncated event prefixes
- `w/ Enrage (tribute to...)` → matched Rage Against The Machine — opener prefix leaking

### CSV Report for Daily Video Verification

Modified `scripts/verify_videos.py` to generate CSV alongside the text report:
- Combined CSV with Section/Artist/Venue/Date/Video URL/Detail columns
- Sections: Verified, Rejected, No Preview
- When using `--output report.txt`, also writes `report.csv`
- In nightly pipeline, saves to `qa/video-report-{date}.csv` and posts comment on GitHub Issue

### Workflow Updates

`.github/workflows/scrape.yml` updated:
- Added "Spotify artist enrichment" step between validate and verify (`continue-on-error: true`)
- Added `qa/spotify_cache.json` and `qa/video-report-*.csv` to git add in commit step

### Remaining Setup
- Add `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` as GitHub Secrets
- Phase 2 (next session): Wire Spotify signals into `verify_videos.py` as modifiers — review enrichment data first, then tune thresholds

### Manual Video Review — High Spotify Popularity No-Preview Queue

Used Spotify popularity scores from `qa/spotify_cache.json` to triage the no-preview queue, reviewing highest-popularity artists first. For each: searched YouTube, verified channel/video identity, presented recommendation, waited for user approval, then added override + updated show data.

**Reviewed & accepted (14 total):**

| Artist | Venue | Spotify Pop | Video | Channel/Notes |
|--------|-------|------------|-------|---------------|
| Guitarricadelafuente | Bowery Ballroom (x2) | 61 | b_f2qiL_nP4 | Verified channel, accepted despite 13M views (Latin Grammy winner) |
| Borgeous | Elevation 27 | 52 | Yb5j4GheNTk | Accepted despite 22M views (Spinnin' Records = legitimate label) |
| Bryant Barnes | El Club | 63 | Srk8kGK16oA | Verified channel (445K subs), 3.8M views |
| Goldie Boutilier | El Club | 56 | Ka_tHvcyD3k | Verified channel (23.1K subs), 157K views |
| Rochelle Jordan | El Club | 54 | xqVpSvquWFM | Verified channel (26.5K subs), 152K views, EMPIRE distribution |
| Orbit Culture | El Club | 54 | 3RndtM2br5A | Verified channel (121K subs), 645K views, Century Media Records |
| Alex Sampson | El Club | 51 | QBsIYrePl2o | Verified channel (483K subs), 715K views |
| Ratboys | El Club | 48 | KYUMoL9FrIA | Verified channel (3.31K subs), 55K views, New West Records |
| Beauty School Dropout | El Club | 47 | yKZ8Qk-z4gY | Verified channel (21K subs), 217K views, Vevo |
| Mindchatter | El Club | 46 | -LwiIDb3iKc | Verified channel (12.8K subs), 565K views |
| Penelope Road | El Club | 44 | bKcTK9hibhM | Verified channel (9.28K subs), 183K views, Warner Records |
| Eidola | El Club | 44 | xOD9ic2bIAY | Rise Records channel (3M subs), 340K views |
| Capstan | El Club | 42 | d1VqBzXvPnE | Verified channel (11.2K subs), 489K views, Fearless Records |

**Reviewed & rejected (1):**
- **DANCE** (The Social, pop 30) → Matched "Goombay Dance Band - Seven Tears" — completely wrong artist. Added null override.

All 14 overrides added to `scrapers/overrides.json`, show data updated in `data/shows-elclub.json` (11), `data/shows-boweryballroom.json` (2), `data/shows-elevation27.json` (1).

**Key finding — Bandsintown as verification signal:**
YouTube video pages display Bandsintown tour dates inline. For 8+ of the El Club artists reviewed, the Bandsintown widget on the YouTube page confirmed the exact El Club Detroit show date — providing independent, automated proof that the YouTube channel belongs to the correct touring artist. This is a very strong identity signal (+++) that could potentially be used to strengthen the verifier's confidence in matches. **Explore Bandsintown tour date confirmation as a verification signal next session.**

**Remaining El Club artists (lower Spotify popularity, not yet reviewed):**
- SZN4 (pop 39), Hieroglyphics (pop 39), Super Future (pop 35), Eggy (pop 24), Emo Nite (pop 0)
- Plus event names: It's A 2000s Party: Detroit, A Night With The Saunderson Brothers

### Next Steps
- **Bandsintown signal**: Evaluate using tour date confirmation as a +++ verification signal in the automated verifier
- Add Spotify credentials as GitHub Secrets
- Phase 2: Wire Spotify signals into verifier (cross-ref top tracks vs video titles, no-match = strengthen rejection)
- Continue manual review: remaining El Club artists, then Kings/Lincoln/Local 506/Mohawk/Motorco/Pinhook entries
- El Club scraper investigation (why so many shows had no video from scraper)
- Multi-act feature (discussed, not started)
- Finalize video disclaimer wording
- Reddit post (outreach/reddit-post-triangle.txt)
- Verify first automated weekly report Monday Mar 2

---

## Session: Feb 24, 2026 (continued — session 2)

### El Club Video Coverage — Complete

Finished reviewing all remaining El Club artists. All 4 active shows now have video assignments:

| Artist | Spotify Pop | Video | Channel/Notes |
|--------|------------|-------|---------------|
| Hieroglyphics | 39 | V8B8bbrkETQ | UPROXX Video (741K views), also KEXP live |
| Eggy | 24 | oa0WTcgEkFU | Flightless Records (5.6K views, 2025 album) |
| Emo Nite | 0 | VzJa8Eql6A8 | @EmoNiteLA (45.1K subs, Post Malone at Emo Nite) |
| A Night With The Saunderson Brothers | n/a | LZzxq4hLFhU | Boiler Room: Detroit (19K views, verified 5.1M subs) |

**El Club re-added to site** — was removed due to poor matching. Now at full video coverage. Added button to Beyond the Triangle section in index.html, confirmed working on mobile.

### Cross-Venue No-Preview Queue — Systematic Review

Created `scripts/no_preview_report.py` to list all remaining no-preview shows sorted by Spotify popularity. Started at 32, worked through searchable artists.

**Reviewed & accepted (7):**

| Artist | Venue | Video | Channel/Notes |
|--------|-------|-------|---------------|
| JULIA. | Kings | VMePxmKXCH0 | @JULIA.theband (78 subs), local NC funk band |
| Robert Morton | Local 506 | Az3RcZfWcvc | Own channel (29 subs), NPR Tiny Desk submission, Chapel Hill |
| Fish Hunt | Pinhook | rVieMw_GLSU | Own channel (614 subs), "Go My Way" Official MV, VHS Records |
| Invisible Cities | Pinhook | eIK1Qw9K9ZY | @Invisible-Cities-NYC (1 sub), full album, Brooklyn death rock |
| Lifeguard | Pinhook | Bjn2LoYQ2KY | Verified channel (2.33K subs), "Ultra Violence" Official MV, Chicago punk |
| SUM SUN (Rikkies show) | Bowery Ballroom | CR0nXySqqPo | Verified channel (976 subs), "Blame It On The Rain" Official MV, 179K views. Bandsintown confirmed Feb 28 Bowery show. |

**Reviewed & skipped (4):**
- **The Ruckus** (Bowery) — Topic channel only, 25 subs, 238 views
- **Oof Fighters** (Mohawk) — Tribute act, only Foo Fighters results
- **The Rikkies** (Bowery) — Only 9-15 year old live clips. SUM SUN (co-headliner) video assigned instead
- **LUEWWD XX** (Motorco) — Topic channel (LW¥XX¥) with 8 views. Too thin for a preview

### Lessons Learned — Manual Review Calibration

**Don't skip legitimate touring bands:** Initially recommended SKIP for Invisible Cities (1 sub, 28 views on full album). User corrected — the criteria should be "is this a real touring act" not "is their YouTube big enough." Google AI Overview confirmed Brooklyn death rock/post-punk band with active 2025/2026 tour.

**Check for the brand's own channel:** Initially recommended null override for Emo Nite (event, not a band). User said to look again — found @EmoNiteLA with 45.1K subs and 330 videos. Events can have strong YouTube channels.

**User watches along:** For Eggy, user had navigated to a more current video than what I clicked. Always check what the user has up before proceeding.

### Remaining No-Preview Queue

~24 shows remain without video. All are events, DJ nights, tributes, showcases, or null overrides — not searchable bands. **The searchable artist portion of the no-preview queue is now exhausted.**

### Next Steps
- Add Spotify credentials as GitHub Secrets
- Phase 2: Wire Spotify signals into verifier
- Multi-act feature (discussed, not started)
- Finalize video disclaimer wording
- Reddit post (outreach/reddit-post-triangle.txt)
- Verify first automated weekly report Monday Mar 2
- Consider encoding manual review criteria into verifier (label allowlist, verification badge, Bandsintown confirmation)

---

## Session: Feb 25, 2026

### Code Review — Foundation Audit

Ran 5 parallel code review agents across the codebase (base_scraper.py, verify_videos.py, spotify_enrich.py, workflow/overrides, frontend). Compiled 26 findings into 3 priority tiers:

**Tier 1 (before adding venues):** Shared utils module, workflow failure notifications, consolidated requirements.txt, venues.json config
**Tier 2 (next session):** Specific exception handling, centralized config, pluggable verification architecture, overrides metadata
**Tier 3 (ongoing):** Frontend performance, caching, test coverage

### Multi-State Navigation — Implemented

Replaced hardcoded venue buttons with a dynamic two-dropdown system (State + Region) driven by `data/venues.json`.

**Architecture decisions:**
- `data/venues.json` = single source of truth for all venue metadata (state → region → venue hierarchy)
- State dropdown + Region dropdown — always visible (no auto-skip for single-region states, because users in other cities need geographic context)
- Per-region taglines (e.g., "What's playing in the Triangle tonight?" → "What's playing in Orlando tonight?")
- "Don't see your favorite small venue? Send us a suggestion" text between dropdowns and venue buttons
- Removed "Beyond the Triangle" section entirely — all venues now accessible via dropdowns

**Files created:** `data/venues.json`
**Files modified:** `index.html` (dropdowns + dynamic containers), `app.js` (complete nav rewrite — loads config, builds dropdowns, renders buttons), `styles.css` (dropdown styles, mobile responsive)

**Current venue coverage:** 6 states, 6 regions, 11 venues
- NC / Raleigh-Durham: Cat's Cradle, Local 506, Motorco, The Pinhook, Lincoln Theatre, Kings
- FL / Orlando: The Social
- MI / Detroit: El Club
- NY / New York City: Bowery Ballroom
- TX / Austin: Mohawk
- VA / Virginia Beach: Elevation 27

### Shared Python Utils Module — Created

Created `scrapers/utils.py` to eliminate duplicated code across three Python files.

**Functions extracted:**
- `load_env_var(key)` — unified .env reader, checks environment first, strips quotes (fixed a bug in base_scraper.py's version that didn't strip quotes)
- `normalize(text)` — simple lowercase + strip non-alphanumeric (was identical in verify_videos.py and spotify_enrich.py)
- `normalize_artist(name)` — richer normalization: strips "the", tour suffixes, parentheticals (was `_normalize()` in base_scraper.py)
- `name_similarity(a, b)` — float 0-1 scorer (was only in spotify_enrich.py)

**Files updated to import from utils:**
- `scrapers/base_scraper.py` — `_load_api_key()` → `load_env_var()`, `_normalize()` → `normalize_artist()`
- `scripts/verify_videos.py` — `load_api_key()` → `load_env_var()`, `normalize()` → shared
- `scripts/spotify_enrich.py` — `load_spotify_credentials()` → `load_env_var()`, `normalize()` + `name_similarity()` → shared

### Workflow Failure Notifications — Expanded

Updated `.github/workflows/scrape.yml`:
- All 10 scraper steps now have `id:` and `continue-on-error: true` — one venue failure no longer halts the pipeline
- Alert GitHub Issue now reports on all 13 tracked steps (10 scrapers + monitor + validate + verify)
- Alert title includes failure count (e.g., "Scrape Alert — 2026-02-25 (2 failures)")
- Full pass/fail table in alert body

### Consolidated requirements.txt

Merged `scrapers/requirements.txt` (requests, beautifulsoup4) and root `requirements.txt` (google-analytics-data, google-auth) into a single root file. Deleted `scrapers/requirements.txt`. Both workflows (`scrape.yml`, `weekly-report.yml`) now use `pip install -r requirements.txt`.

### Key Files (updated)
- `scrapers/utils.py` — **new** shared utilities (normalize, env loading, name similarity)
- `data/venues.json` — **new** venue config (single source of truth for state/region/venue hierarchy)
- `.github/workflows/scrape.yml` — expanded failure notifications, consolidated deps
- `requirements.txt` — consolidated all Python dependencies

### Next Steps
- Multi-act opener splitting (task #8) — show individual band names with separate play buttons
- Spotify Phase 2: wire signals into verifier
- Continue adding venues (foundation now supports it)
- Finalize video disclaimer wording
- Reddit post (outreach/reddit-post-triangle.txt)
- Verify first automated weekly report Monday Mar 2

---

## Session: Feb 25, 2026 (continued — session 2)

### Multi-Act Opener Splitting — Implemented

Opener fields with multiple band names (e.g., "Trace Mountains, honeygaze") now render as individual clickable elements instead of one blob.

**New method `splitOpeners()` in `app.js`:**
- Strips `w/ ` prefix
- Splits on `, ` (comma+space) and ` / ` (space-slash-space)
- Strips leading conjunctions (`and `, `& `, `+ `) from each token
- Filters noise words (`Special Guests!`, `TBA`, `More!`)
- Does NOT split on bare ` and ` — too risky ("Florence and the Machine", "Buck Swope and Green Room")

**Display behavior:**
- First name gets the existing video (if any) with full play styling
- All other names get dimmed play icons and trigger the no-preview popup when clicked
- Every name is keyboard-accessible (tabindex, role="button", Enter/Space handlers)
- GA4 `sample_play` events fire with the individual band name, not the full opener string

**CSS additions:**
- All opener names are clickable (cursor: pointer)
- Non-video names show dimmed play icon on hover
- Focus-visible ring on all opener names (replaced the old has-video-only rule)

**Files modified:** `app.js`, `styles.css`

### RIP MTV — Manual Rejection + Pipeline Gap Analysis

Found "RIP MTV" at Mohawk serving a 7-minute commentary video by "Stevo32Drums" about MTV shutting down. This is an event (themed party with "Unplugged Sets, TRL photobooth, Throwback Videos" as openers), not a band.

**Nulled the video and traced why the pipeline missed it:**

| Layer | Signal Present | Why It Didn't Reject |
|-------|---------------|---------------------|
| **Scraper** | "RIP" not in EVENT_KEYWORDS | Missing keyword |
| **Verifier** | Channel warning ("Stevo32Drums" ≠ "RIP MTV") | Only rejects channel mismatch at 2M+ subs |
| **Spotify** | Matched "R.I.P." (wrong artist, popularity 24) | Phase 1 = annotation only, not a gate |
| **Opener** | "Unplugged Sets, TRL photobooth, Throwback Videos" | Zero validation on opener content |

**Scraper fix:** Added case-sensitive `^R.I.P.` check to `_clean_artist_name()` (separate from the case-insensitive EVENT_KEYWORDS regex to avoid matching bands like "Rip Tide"). Also added "Photobooth" to EVENT_KEYWORDS.

**Files modified:** `data/shows-mohawk.json`, `scrapers/base_scraper.py`

### Spotify Phase 2 — Verifier Integration Complete

Wired Spotify enrichment data into `verify_videos.py` as a rejection modifier. This was the missing piece that would have caught RIP MTV automatically.

**Two new rules:**
1. **Not found on Spotify + channel mismatch → reject** — neither source can confirm the artist exists
2. **Close/partial Spotify match + channel mismatch → warning** — logged in metadata but not a hard reject (could be a real indie band on a label channel)

**Implementation:**
- Spotify cache loaded early in `main()` (was previously loaded only for report annotations)
- `verify_video()` now accepts optional `spotify_entry` parameter
- Spotify match confidence and popularity stored in verification metadata
- No changes to Spotify enrichment script — reads the same cache

**Dry-run results:** 2 additional bad matches caught that would have slipped through before:
- "Rivalry Night" — event, not a band (no Spotify match + channel mismatch)
- SXSW showcase entry — event (no Spotify match + channel mismatch)

**Files modified:** `scripts/verify_videos.py`

### Bandsintown API — Noted for Future

User noted Bandsintown as a potential additional artist validation source, budget permitting. Would confirm an artist is a real touring act. Not yet planned — evaluate after monitoring Spotify Phase 2 effectiveness.

### Next Steps
- Monitor tonight's pipeline — first run with scraper RIP fix + Spotify Phase 2 rejection logic
- Continue adding venues (foundation supports it)
- Finalize video disclaimer wording
- Reddit post (outreach/reddit-post-triangle.txt)
- Verify first automated weekly report Monday Mar 2
- Consider encoding more manual review criteria into verifier (label allowlist, verification badge, artist-tier-aware caps)
- Bandsintown API evaluation (budget permitting)

---

## Session: Feb 25, 2026 (continued — session 3)

### Smarter Verifier — Trusted Labels, VEVO Detection, Spotify-Aware View Caps

Encoded manual review patterns into `scripts/verify_videos.py` to reduce false rejections. Previously, a flat 5M view cap and simple channel-name matching caused legitimate artists on label channels to get rejected — then we'd override them one by one. Now the verifier handles these cases automatically.

**Three new features:**

**1. Trusted label allowlist (14 labels):**
Nuclear Blast, Epitaph, Fueled By Ramen, Spinnin', Secret City, Innovative Leisure, SideOneDummy, Rise, Fearless, Century Media, New West, Flightless, Warner, Carpark. Keys are pre-normalized for O(1) lookup. Trusted channels bypass: channel mismatch rejection, upload age rejection, Spotify no_match rejection. View cap raised to 50M.

EMPIRE was initially included but removed — "empire" is too generic a normalized key. At our nightly volume (~5-10 new checks), the risk of a false positive outweighs the cost of manually overriding a legitimate EMPIRE artist.

**2. VEVO detection:**
Checks if normalized channel name ends with "vevo". Same bypasses as trusted labels — channel mismatch, age, Spotify no_match, 50M view cap.

**3. Spotify-popularity-aware view caps:**
- Popularity >= 70: no cap (major artist)
- Popularity >= 50: 50M cap
- Popularity >= 30: 10M cap
- Below 30 or no Spotify data: 5M default

**Dry-run results:**
- Punchline now passes (Fueled By Ramen detected, was rejected for 15.4M subs + 20yr age)
- Only 6 videos checked — 264 already verified + 40 overrides from prior runs
- Previously rejected artists (Borgeous, Burning Witches, Death Lens, Gogol Bordello, Aterciopelados, POWFU, Music For The Masses) had youtube_ids nulled in prior runs — scrapers will reassign on next nightly run, and the new logic will let them through

**Confirmed from video_states.json — all 8 target artists would now pass:**

| Artist | Old Rejection | New Result |
|--------|--------------|------------|
| Borgeous | 22.9M views + Spinnin' 32M subs | Spinnin' trusted → 50M cap, skip mismatch |
| Burning Witches | Nuclear Blast 3.35M subs | Trusted label, skip mismatch |
| Death Lens | Epitaph 3.93M subs | Trusted label, skip mismatch |
| Punchline | Fueled By Ramen 15.4M subs + 20yr | Trusted label, skip mismatch + age |
| Gogol Bordello | 14.3M views + SideOneDummy | Trusted label → 50M cap, skip age |
| Aterciopelados | 42M views, VEVO | VEVO → 50M cap |
| POWFU | 8.2M views, VEVO | VEVO → 50M cap |
| Music For The Masses | Nuclear Blast 3.35M subs + 20yr | Trusted label, skip mismatch + age |

**Bryce Vine (98.7M views) still fails** — channel matches artist name (not a label/mismatch issue), Spotify pop 59 → 50M cap, but 98.7M > 50M. Needs manual override or Spotify pop to climb above 70.

**Safety confirmed — bad matches still rejected:**
- RIP MTV: no Spotify + channel mismatch (Stevo32Drums not a label)
- Oof Fighters: Foo Fighters channel not in label list
- Events/random: no Spotify + no trusted channel

**Metadata logging:** Every bypass is recorded in verification metadata (`trusted_label`, `vevo_channel`, `channel_override`, `age_override`, `spotify_override`, `view_cap_reason`) for auditability.

**Files modified:** `scripts/verify_videos.py`

### Next Steps
- Monitor tonight's nightly run — first with trusted labels + VEVO + Spotify-aware caps + Neighborhood Theatre
- Previously rejected artists should get reassigned by scrapers and pass the new logic
- Check Bryce Vine's Spotify popularity when he comes through; may need manual override
- Continue adding venues (Charlotte done, next city TBD)
- Finalize video disclaimer wording
- Reddit post (outreach/reddit-post-triangle.txt)
- Verify first automated weekly report Monday Mar 2
- Bandsintown API evaluation — decided against for now (see below)

### Bandsintown API — Evaluated and Deferred

Evaluated Bandsintown API for artist validation / show confirmation. Decision: not worth pursuing now.

**Why not:**
- API keys are per-artist, not per-platform. Bulk querying hundreds of artists requires a partnership deal — negotiation, contract, possibly fees.
- YouTube + Spotify + trusted labels already cover the validation signals Bandsintown would provide.
- The one unique thing (confirming "artist X plays venue Y on date Z") isn't needed — our scrapers pull directly from venue calendars, which is the authoritative source.

**Where it could matter later:** If we ever replace scraping with a single API for venue calendars, Bandsintown becomes interesting as a data source. But that's a different architecture, not a validation layer. Revisit if partnership access becomes available or scraping needs replacement.

---

## Session: Feb 25, 2026 (continued — session 4)

### Neighborhood Theatre (Charlotte, NC) — Scraper Built & Deployed

Added Charlotte as the second NC region. Neighborhood Theatre is an independent small venue — exactly our target — and Charlotte is NC's biggest city with reach from our local Reddit channels.

**Scraper:** `scrapers/scraper_neighborhood.py`
- Same Ticketmaster widget (`tw-` CSS classes) as Elevation 27 — copy-and-adapt pattern
- Calendar URL: `https://neighborhoodtheatre.com/calendar/`
- Custom `_clean_artist_name()` override handles dash-tour patterns more aggressively than the base class (e.g., "MAGGIE LINDEMANN – I Feel Everything Tour" → "MAGGIE LINDEMANN")
- Also strips colons and "ft." suffixes (base class only handles "feat.")
- Opener extraction from title ("with" / "w/" patterns)

**First run results:** 24 shows, 22 with YouTube video, 24 with images

**Notable artists:** Maggie Lindemann, Old Crow Medicine Show, Yonder Mountain String Band, Lotus, Mike Gordon, Carter Faith, Eggy, Satsang, Mo Lowda & The Humble

**Name cleaning examples:**
- "MAGGIE LINDEMANN – I Feel Everything Tour" → "MAGGIE LINDEMANN"
- "Doc 103: Celebrating Doc Watson w/ Jack Lawrence..." → "Doc 103" (opener extracted)
- "JOHN COWAN TRIO ft. Luke Bulla & Ethan Ballinger" → "JOHN COWAN TRIO"
- "The Rock & Roll Playhouse: Music of The Beatles + More for Kids" → "The Rock & Roll Playhouse"

**Files created:** `scrapers/scraper_neighborhood.py`, `data/shows-neighborhood.json`
**Files modified:** `data/venues.json` (Charlotte region under NC), `.github/workflows/scrape.yml` (scraper step + alert)

**Venue count:** 7 states, 7 regions, 12 venues

---

## Session: Feb 25, 2026 (continued — session 5)

### The Orange Peel (Asheville, NC) — Scraper Built & Deployed

Added Asheville as the third NC region. The Orange Peel is one of the most well-known independent venues in the Southeast — strong lineup, strong brand.

**Scraper:** `scrapers/scraper_orangepeel.py`
- eventWrapper pattern (like Lincoln Theatre and The Pinhook), not Ticketmaster widget
- Calendar URL: `https://theorangepeel.net/events/`
- ETIX ticketing (not Ticketmaster)
- Custom `_clean_artist_name()` override with " / " multi-band splitting, aggressive dash-tour stripping
- Added Orange Peel-specific event keywords: Comedy, Standup, Contest, Roast, K-Pop Kids Party
- Opener parsing handles `<br>`-separated names within single h4 elements (use `separator=', '` in `get_text()`)
- Filters descriptive h4 text from openers (e.g., "20th anniversary of the album in its entirety" — not an opener name)

**Issues found and fixed during build:**
1. h4 openers concatenated without separators ("No PressureHaywireSecret World") — fixed with `get_text(separator=', ')`
2. Multi-band bill not split ("Alla Prima / Proxima System / ...") — added " / " splitting
3. Comedy events not filtered ("The Slice of Life Comedy Asheville Spring Standup Contest", "Roast Of Asheville") — added OP_EVENT_KEYWORDS
4. Cat Power's "20th anniversary..." descriptive text parsed as opener — added descriptive text filter

**First run results:** 23 shows, 23 with YouTube video, 23 with images

**Notable artists:** Wax Tailor, Lotus, Aly & AJ, Gary Numan, Cat Power, The Hives, Old Crow Medicine Show, Drain, moe., Robert Earl Keen, Mike Gordon, Donna The Buffalo

**Files created:** `scrapers/scraper_orangepeel.py`, `data/shows-orangepeel.json`
**Files modified:** `data/venues.json` (Asheville region under NC), `.github/workflows/scrape.yml` (scraper step + alert, now 15 steps in alert table)

**Venue count:** 6 states, 8 regions, 13 venues (3 NC regions: Triangle, Charlotte, Asheville)

---

## Session: Feb 26, 2026

### First Nightly Run Review — Orange Peel + Neighborhood Theatre

Reviewed the Feb 26 nightly scrape results (first automated run with both new venues).

**Scrape alert (Issue #16):** 1 failure — Data Validation. All 13 scrapers passed (including both new ones). Scrape Monitor also passed.

**Video report (Issue #15):**
- 16 verified, 97 rejected, 244 already verified, 40 overrides
- Orange Peel: 7 verified (S.G. Goodman, Tab Benoit, Jordan Jensen, Tremours, The Chats, Nolen Durham, Old Crow Medicine Show)
- Neighborhood Theatre: 4 verified (ALEXSUCKS, Mike Gordon, Walter Trout, Walker Montgomery)
- Trusted labels/VEVO working: Punchline (Fueled By Ramen), Skullcrusher (VEVO), Snowblinder (Nuclear Blast)
- Mass "could not fetch video metadata" rejections — YouTube oEmbed rate limiting from adding two new venues at once. Should self-heal over next few nights as verified videos are skipped.

**CSV attachment:** Not a downloadable file — GitHub Issues API can't attach files. CSV data is embedded as text in a comment on the issue, and also committed to `qa/video-report-2026-02-26.csv`.

### Validation Baseline — Built & Deployed

The validation script (`scripts/validate_shows.py`) was exiting with code 1 every night because it had no memory — it re-flagged every known warning (long names, event keywords, missing videos) from scratch each run. This made the scrape alert always show "1 failure" even when nothing changed.

**Fix:** Added baseline tracking via `qa/validation_baseline.json`. The script now:
1. Hashes each warning message (MD5)
2. Compares against the baseline from the previous run
3. Labels each warning as NEW or KNOWN
4. Saves the current set as the new baseline
5. Exits 1 only if there are NEW warnings — known warnings exit 0

Summary line: `NEW: 0 | KNOWN: 54 | RESOLVED: 0`

This scales with venue growth — adding a new venue generates a one-time burst of new warnings, then they go quiet. The RESOLVED count tracks warnings that disappear (show expired or got fixed).

**Files modified:** `scripts/validate_shows.py`, `.github/workflows/scrape.yml` (added `qa/validation_baseline.json` to commit list)
**Files created:** `qa/validation_baseline.json`

### Daily Report Restructure

Analyzed the three email notifications from last night's nightly run by importing them into Excel:
- **Issue #13** (formatted report): Verified (11), Rejected (11), No Preview Queue (35) — truncated, readable
- **Issue #15** (CSV comment): 204 rows covering all shows — complete but required Excel Text-to-Columns to read
- **Issue #16** (scrape alert): All 13 scrapers passed, only Data Validation failed (known issue, fixed with baseline)

**Key finding:** Issue #13 and #15 overlap heavily. Column-by-column comparison confirmed the CSV covers everything the formatted report has, plus more rows and more detail. The formatted report was a truncated, prettier duplicate.

**oEmbed rate limiting diagnosis:** 96 of 97 rejections were "could not fetch video metadata" — not real content problems. Adding Orange Peel + Neighborhood Theatre at once caused a burst of oEmbed requests. These should self-heal as the verifier skips already-verified shows on subsequent runs.

**Decision:** Drop the formatted text report entirely. Keep one CSV committed to `qa/`. Replace the GitHub Issue with a readable markdown summary.

**New report structure (3 sections):**

1. **Tonight's Delta** — What changed in this run:
   - Newly Verified table (Artist | Venue | Date | Spotify | Detail)
   - Newly Rejected table (Artist | Venue | Date | Spotify | Reason)
   - Recovered table (previously rejected, now verified)
   - Recovery detection: snapshot `video_states.json` before verification loop, compare after

2. **Full Inventory** — Coverage stats for all shows:
   - Status breakdown table (Verified | Rejected | No Preview | Override counts + percentages)
   - Per-venue one-liner (e.g., "Cat's Cradle 11/11 · Local 506 24/25")
   - Link to committed CSV file

3. **Accuracy Tracking** — Progression over time:
   - Today's accuracy % and avg confidence (from latest audit)
   - Yesterday and 7-day average comparison
   - Override count
   - Data stored in new `qa/accuracy_history.json` file

**Code changes in `scripts/verify_videos.py`:**
- New helpers: `spotify_csv_indicator()`, `load_latest_audit()`, `load_accuracy_history()`, `save_accuracy_history()`, `compute_inventory()`
- Replaced `build_report()` with `build_issue_body()` — generates GitHub-flavored markdown
- Modified `build_csv()` — added `Changed` column ("New", "Recovered", or blank) for Excel filtering
- Modified `post_github_issue()` — uses `--body-file` with tempfile, dropped CSV comment entirely
- Modified `main()` — snapshots `old_states` before verification loop, appends to accuracy history

**Testing:** Local run produced correct output — recovery detection worked (Los Straitjackets tagged as Recovered), markdown tables rendered properly, CSV had new Changed column, accuracy history file created with yesterday/7-day comparisons.

**Commit:** `b0dd8dc` — "Restructure daily video report — markdown summary + improved CSV"

**Manual scrape triggered** after push to recover the 96 oEmbed failures immediately rather than waiting for tonight. YouTube API budget impact: ~2% of daily quota. oEmbed is free. Spotify not called by verifier (reads local cache only).

### Next Steps
- Check manual scrape results (pipeline running)
- Decide on Reddit intro post timing (outreach/reddit-post-triangle.txt)
- Continue adding venues (more NC? or expand other states?)
- Finalize video disclaimer wording
- Verify first automated weekly report Monday Mar 2
- Report delivery format TBD (GitHub Issue email vs localsoundcheck.com/report)

---

## Session: Feb 27, 2026

### Code Review & Cleanup

Before implementing the quota fix, ran code quality review across all pipeline scripts. Found and fixed:

1. **Duplicated retry logic** — `get_video_metadata()` and `get_channel_metadata()` in `verify_videos.py` had identical retry/backoff code. Extracted shared `_youtube_api_get()` helper (~40 lines removed net).
2. **Dead function** — `spotify_indicator()` in `verify_videos.py` was defined but never called (only `spotify_csv_indicator()` was used). Removed.
3. **Redundant normalize wrappers** — Both `verify_videos.py` and `spotify_enrich.py` had local `normalize()` functions that just called the shared `_normalize` from utils. Removed wrappers, updated call sites to use `_normalize` directly.

### QA Documentation Update

All three QA docs were stale. Updated before code changes:

- **qa/README.md** — Complete rewrite reflecting current 12+ file inventory
- **qa/verification-log.md** — Added Runs 2-6 (Feb 24-27), updated calibration notes with full tiered view cap table, all 14 trusted labels, VEVO detection, Spotify identity signals. Added Known Issues section about quota exhaustion.
- **qa/video-matching-logic.md** — Added Phase 2 (Spotify enrichment), corrected quota budget from "510-1,020" to actual ~9,840 units/day, added view count caps table with all tiers

### YouTube API Quota Fix — Implemented

**Problem:** Scrapers consumed ~9,700 of 10,000 daily YouTube API quota units before the verifier ran. Verifier got 403 (quota exhausted) on nearly all API calls — couldn't verify new videos. Created a cascading failure: rejected → null → re-search next night → more quota burned.

**Fix (two parts):**

**Part 1 — Separate verifier API key:**
- `verify_videos.py` now prefers `YOUTUBE_VERIFIER_API_KEY` with fallback to `YOUTUBE_API_KEY`
- Each API key in Google Cloud gets its own 10K daily quota pool
- Created "YouTube Verifier Key" in Google Cloud Console (project: polar-pilot-488221-v0), restricted to YouTube Data API v3
- Added as GitHub Secret `YOUTUBE_VERIFIER_API_KEY`
- `.github/workflows/scrape.yml` updated to pass the new secret to the verify step

**Part 2 — Rejection-aware search filtering:**
- `base_scraper.py` now loads `qa/video_states.json` at startup
- Artists rejected by the verifier within the last 7 days are skipped (no API search)
- Testing showed ~100 artists would be skipped, saving ~10,000 quota units/night
- After 7 days, cooldown expires and scraper re-searches (in case artist got a new video or verifier rules changed)

**Expected result tonight:** Scrapers use ~5,000-6,000 units (down from ~9,700). Verifier uses ~140 units on its own dedicated key. No more quota starvation.

### Pipeline Overview Documentation

Created `docs/pipeline-overview.md` — plain-language 11-step walkthrough of the full nightly pipeline, from GitHub Actions trigger through commit. Includes the cascading failure explanation and notes on the quota fix.

### External Accuracy Review — Evaluated

User shared a 6-point external review of the video matching pipeline. Evaluated each against the actual codebase without making changes:

1. **YouTube Shorts filtering** — Not needed; Shorts have normal video IDs and our verifier checks (view count, channel match, upload date) already catch bad ones.
2. **Multi-language title matching** — Already handled; `name_similarity()` uses token overlap which works across transliterations.
3. **Label allowlist staleness** — Low risk at 14 labels; they're major labels that don't rebrand. Can revisit annually.
4. **Quota spike protection** — Already mitigated by the rejection-aware filtering + separate API key.
5. **oEmbed fallback chain** — Audit script uses oEmbed separately with 0.3s delay; verifier uses Data API. No chain to break.
6. **Video duration check** — Worth doing. Zero extra API cost (add `contentDetails` to existing `videos` call). Flag videos outside 1-15 min range. **Parked for later.**

### Files Modified
- `scripts/verify_videos.py` — cleanup + verifier API key support
- `scripts/spotify_enrich.py` — removed normalize wrapper
- `scrapers/base_scraper.py` — rejection-aware search filtering
- `.github/workflows/scrape.yml` — pass YOUTUBE_VERIFIER_API_KEY
- `qa/README.md` — rewritten
- `qa/verification-log.md` — updated with Runs 2-6
- `qa/video-matching-logic.md` — updated for 4-phase architecture
- `docs/pipeline-overview.md` — **new**, plain-language pipeline walkthrough

**Commit:** `4e38585` — "Code cleanup, quota fix, and QA docs update"

### Next Steps
- Monitor tonight's nightly run — first with separate verifier API key + rejection filtering
- Video duration check (parked, zero extra API cost)
- Report delivery Option C: HTML email via Gmail SMTP + Google Sheets for detail
- Continue adding venues (next city TBD)
- Finalize video disclaimer wording
- Reddit post (outreach/reddit-post-triangle.txt)
- Verify first automated weekly report Monday Mar 2
