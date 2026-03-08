# Local Soundcheck — Standard Operating Procedures

Living document. Updated as we learn. Claude references this before making pipeline changes.

---

## 0. Reviewing Reports

**Before reviewing the daily report, `git pull` to sync with the nightly pipeline commit (3:30 AM ET).**

When the user references data from the live spreadsheet, treat it as ground truth. The Google Sheet is the authoritative report output — if the user says an entry exists, work with it. Don't waste cycles trying to locate it locally before engaging with the substance.

---

## 1. Override Authority Chain

**Rule: Overrides are the highest authority. They are checked first, everywhere, always.**

Overrides represent human decisions. No automated system — smart filtering, verifier, video_states, audit scores — can block or overwrite an override.

### Decision priority (top wins):
1. `overrides.json` — manual assignment (video ID or null)
2. Verifier — promotes or rejects scraper candidates
3. Scraper smart filtering — reuse or re-search based on confidence
4. YouTube API search — find new candidates

### Where overrides are checked:
| Location | What happens |
|----------|-------------|
| `process_shows_with_youtube()` | **Primary check.** Before `_should_search()` runs, overrides are applied directly. No further search or filtering. |
| `get_youtube_id()` | **Safety net.** Checks overrides again in case the primary check was bypassed. |
| Verifier main loop | Skips verification entirely for overridden artists. |
| `video_states.json` marking | Null overrides always overwrite prior state (verified, rejected, etc.). |

### What we learned:
- **Feb 2026:** Overrides were only checked inside `get_youtube_id()`. Smart filtering (`_should_search()`) could skip that function entirely for rejected artists. Result: overrides for Gogol Bordello, Mint Field, Heated were silently ignored.
- **Mar 5, 2026:** Fixed by checking overrides at the top of the decision chain, before any filtering logic runs.

---

## 2. Adding or Changing an Override

### When to add:
- Artist is an event/DJ night, not a band (null override)
- YouTube search consistently returns wrong artist (null or correct video ID)
- Artist has a specific video we want to use (video ID override)

### Steps:
1. Edit `scrapers/overrides.json`
   - **artist_youtube**: headliner overrides (video ID string or `null`)
   - **opener_youtube**: opener overrides (video ID string or `null`)
   - **show_overrides**: full show corrections (artist name, opener, notice)

2. Check for case variants — Python dict lookup is case-sensitive
   - If the venue site shows "NIGHT MOVES" and "Night Moves" at different times, add both
   - Check existing show data files to see how the name actually appears

3. If adding a null override for an artist that was previously verified:
   - The override will win — `video_states.json` entry gets overwritten at report time
   - No need to manually edit `video_states.json`

4. Test locally: `python3 scrapers/scraper_<venue>.py` (uses ~1-2 API calls per new artist)
   - Verify the override appears in the match log with `tier: "override"`

5. Commit and push — takes effect on next nightly scrape

### Do NOT:
- Run the full pipeline locally (burns shared API quota)
- Edit `video_states.json` manually (the pipeline manages it)
- Add overrides in only one case variant if the name appears differently in show data

---

## 3. Adding a New Venue

### Pre-work:
1. Study the venue website — how are shows listed? Calendar page? RSS feed? API?
2. Check if it's part of a venue group (like Cat's Cradle listing Motorco shows)
3. Identify what data is available: artist, date, opener, doors/showtime, image, ticket URL

### Scraper:
1. Create `scrapers/scraper_<venue>.py` extending `BaseScraper`
2. Set class attributes: `venue_name`, `venue_location`, `venue_website`, `output_filename`
3. Implement `scrape_shows()` — return list of show dicts
4. **CRITICAL**: Call `self.process_shows_with_youtube(shows)` — never call `get_youtube_id()` directly
5. If venue site lists shows for multiple sub-venues, implement `_extract_venue()` using structured data (venue links, URL slugs) NOT full-text search

### Data file:
1. Output goes to `data/shows-<slug>.json`
2. File is auto-created by `save_json()`

### Configuration:
1. Add venue to `data/venues.json` under the correct state/region
2. Fields: `slug`, `name`, `city`, `website`
3. Slug must match the filename: `shows-<slug>.json`

### Workflow integration:
1. Add scraper call to `.github/workflows/scrape.yml`
2. Add data file to the auto-commit list in scrape.yml
3. Add data file to expire, monitor, validate steps if they need explicit file lists

### Testing:
1. Run scraper standalone: `python3 scrapers/scraper_<venue>.py`
2. Run `python3 scripts/validate_shows.py` to check data quality
3. Check the site locally: `python3 -m http.server 8080` and verify shows appear
4. Do NOT run the full pipeline — test each piece independently

### What we learned:
- **Cat's Cradle venue detection bug (Mar 5, 2026):** Full-text search for "motorco" in page content matched an artist bio that mentioned Motorco as a past venue. Fix: use structured venue indicators (CSS selectors, URL slugs) before falling back to text search.
- **Heartwood Soundstage (Mar 8, 2026):** Webflow CMS caps collection lists at 100 items. Site had a hidden 100-item calendar (all past events) and a separate visible grid with upcoming shows. Scraper initially targeted the wrong collection, wasting 26 API calls on past events. **Always do a dry parse first** — print titles + dates without YouTube to confirm you're scraping the right data before enabling API calls.

---

## 4. Modifying Pipeline Logic

### Before changing any decision point, audit these:
1. Does this change affect how overrides are applied? (See Section 1)
2. Does this change affect what appears in the daily report? (CSV, Sheets, email)
3. Does this change affect `video_states.json`? (Persists across runs)
4. Does this change affect what the user sees on the website?
5. Can this change interact with smart filtering (`_should_search()`)?

### The five decision systems (must stay in sync):
| System | File | Persists? |
|--------|------|-----------|
| Overrides | `scrapers/overrides.json` | Yes (manual) |
| Video states | `qa/video_states.json` | Yes (auto) |
| Match log | `qa/match_log.json` | Yes (auto, appended) |
| Show data | `data/shows-*.json` | Yes (auto) |
| Smart filtering | `base_scraper.py` | No (runtime) |

### Testing checklist:
- [ ] Run with `--dry-run` or `--output` to avoid side effects
- [ ] Check that overrides still work after the change
- [ ] Check that the report reflects the change correctly
- [ ] Check that `video_states.json` isn't corrupted
- [ ] Verify the website still displays correctly

### Do NOT:
- Run full scraper pipeline locally mid-day (shared API quota)
- Assume a local test passing means the live run will pass (quota can be exhausted by scrapers before verifier runs)
- Add a new decision point without checking how it interacts with all five systems above

### What we learned:
- **Mar 4, 2026:** Local pipeline run exhausted YouTube API quota. Verifier hit 403 on every call, treating "could not fetch metadata" as rejection. Nulled legitimate videos across show data, video_states, and Google Sheets.
- **Mar 5, 2026:** Multiple fixes needed for override-null shows because the `not in states` guard prevented overrides from overwriting old verified/rejected entries.

---

## 5. Report Filters — What Users See vs. What We See

### Daily report excludes:
- **Expired shows** — past their date, not on the website
- **Override-null artists** — intentional "no video" decisions (events, DJ nights)

### Daily report includes:
- **Verified** — new videos passing verifier tonight (excludes previously-verified artists)
- **Rejected** — videos failing verifier tonight
- **No Preview** — active shows without a video, split into Actionable (top) and Already Reviewed (bottom). Excludes artists already shown in Rejected section.

### Inventory stats include:
- All active (non-expired) shows
- Override-null counted separately as "Override" (not in No Preview count)

### What we learned:
- **Mar 5, 2026:** Expired shows were inflating No Preview count and appearing in the review queue. Override-null shows (Heated, DISCO ALWAYS) showed up as "No video from scraper" because old video_states entries weren't being overwritten.

---

## 6. Quota Management

- YouTube API quota: **10,000 units/day shared across project** (not per key)
- Scrapers use `YOUTUBE_API_KEY`, verifier uses `YOUTUBE_VERIFIER_API_KEY` — same project
- Smart filtering reduces API calls by reusing high-confidence matches
- Overrides use zero API calls

### Safe local testing:
- Single scraper: ~1-5 API calls per new artist (safe)
- `verify_videos.py --dry-run`: ~0-10 API calls for unverified candidates (usually safe)
- `verify_videos.py --output /tmp/test.md`: same as dry-run for API, writes to file
- **Full pipeline**: 100+ API calls — NEVER run locally during the day

---

*Last updated: 2026-03-07*
*Document created after override authority chain audit revealed multiple decision conflicts.*
