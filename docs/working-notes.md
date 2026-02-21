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

### Next Steps
- Multi-act feature: show individual band names with separate video/no-preview indicators for comma/slash-separated opener fields
- Round 2 accuracy: address the 19 low-confidence punch list above
- Consider "and" as band separator for Local 506 (risky — could break names like "Florence and the Machine")
- Manual verification pass on the 13 medium-confidence entries
- Round 2 planning: additional scoring signals based on Round 1 match log data
