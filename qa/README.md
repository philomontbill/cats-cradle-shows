# Quality Assurance

YouTube match accuracy is the core quality metric for Local Soundcheck. A wrong video is worse than no video.

## Pipeline Overview

The video QA pipeline runs nightly after scraping:

```
Scrapers → Spotify Enrich → Verify Videos → Audit → Commit
```

- **Scrapers** find candidate YouTube videos for new/unverified artists
- **Spotify Enrich** confirms artist identity via Spotify API, caches metadata
- **Verifier** checks candidates against view count, channel analysis, Spotify data, upload age
- **Audit** scores all assigned videos via oEmbed and saves timestamped results

## Directory Contents

### Operational State (updated nightly)

| File | Purpose |
|------|---------|
| `video_states.json` | Verification state for every artist — verified, rejected, override, unverified |
| `spotify_cache.json` | Cached Spotify artist metadata (popularity, genres, followers). 30-day TTL |
| `match_log.json` | Scraper match decisions log (artist, video, confidence, timestamp) |
| `validation_baseline.json` | Warning hashes for `validate_shows.py` — suppresses known warnings |
| `accuracy_history.json` | Daily accuracy snapshots (total shows, verified, rejected, accuracy rate) |

### Reports (generated per run)

| File | Purpose |
|------|---------|
| `video-report-YYYY-MM-DD.csv` | Daily verifier report — verified, rejected, and no-preview queues |
| `audits/YYYY-MM-DD_HHMM.json` | Timestamped audit snapshots with per-venue and per-artist scores |

### Documentation

| File | Purpose |
|------|---------|
| `video-matching-logic.md` | Design spec — architecture, decision tree, thresholds, principles |
| `verification-log.md` | Operational log — run results, calibration decisions, threshold changes |

### Scripts

| File | Purpose |
|------|---------|
| `audit_accuracy.py` | Scores all video assignments via YouTube oEmbed (no API key needed) |

### Manual Corrections

| File | Purpose |
|------|---------|
| `corrections.json` | Log of manual corrections (artist name fixes, video overrides) |

## Related Files (outside qa/)

- `scrapers/overrides.json` — Manual YouTube ID overrides and show-level name corrections
- `scripts/verify_videos.py` — The verifier (Phase 3 of the pipeline)
- `scripts/spotify_enrich.py` — Spotify enrichment (Phase 2 of the pipeline)
- `scripts/validate_shows.py` — Data validation (flags bad artist names, missing videos)
- `docs/strategy.md` — Project strategy and operations backlog
