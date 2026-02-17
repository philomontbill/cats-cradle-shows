# Plan: Fill in Artist Spreadsheet Blanks

## Context
The spreadsheet `Spread Sheets/Artist List v1 2-16-2026.xlsx` tracks 84 upcoming shows (Feb-May 2026). Three columns had major gaps:

| Column | Field | Filled | Missing |
|--------|-------|--------|---------|
| F | Instagram | 78 | 6 |
| G | Email/Booking | 7 | 77 |
| H | Website | 23 | 61 |

Both sheets needed updating: "Cat's Cradle Artists" (84 rows) and "NC Local Priority" (12 rows).

## Execution Summary

### Phase 1 — Data Collection (3 parallel tasks)

**Task A: Scraped Cat's Cradle event pages**
- Python script fetched all 120 CC event page URLs
- Extracted artist social links (Instagram, Website, Facebook, Spotify, TikTok)
- Found data for 114 events
- Key finding: event pages embed artist social links as external URLs

**Task B: Web-searched 11 non-CC venue artists**
- Artists at Motorco, Haw River Ballroom, Local 506, AJ Fletcher Opera
- Found website + booking contacts for all 11

**Task C: Web-searched 6 missing Instagram handles**
- Found 5 of 6: @carrborobluegrassfestival, @jasonnarducy, @slow_teeth, @stillnotokaytour, @bigstarband
- Rivalry Night has no dedicated Instagram (it's a Cat's Cradle event concept)

### Phase 2 — Booking Email Research (3 parallel batches)
- 3 agents each searched ~20 artists for booking/management emails
- Used web search for "[artist] booking contact email"

### Phase 3 — Update & Verify
- Python script using openpyxl to write findings into Excel
- Only filled blank cells — never overwrote existing data
- Updated both sheets

## Files Modified
- `Spread Sheets/Artist List v1 2-16-2026.xlsx` — filled blank cells (Instagram, Email/Booking, Website)

## Data Sources
- Cat's Cradle event pages (catscradle.com/events/)
- Web searches for artist booking/management info
- Existing scraper infrastructure pattern (scraper.py, base_scraper.py)
