## Memories

- 3 looks like the most efficient.

## Show Data Quality Checks

When updating or reviewing show data (`data/shows-*.json`), flag entries that look odd:
- **Artist name too long** (60+ chars) — may be a festival/event title instead of a band name
- **Artist contains "Presents", "Festival", "Series", "Showcase"** — event name in the artist field; real band should be extracted
- **Opener has "with" joining multiple bands** — may need to split into artist + opener
- **Missing youtube_id** — no video preview for the show
- **Opener listed but no opener video** — opener won't be playable

Run `python3 validate_shows.py` after scraping or updating show data to catch these automatically.