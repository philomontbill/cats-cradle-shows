# Quality Assurance

YouTube match accuracy is the core quality metric for Local Soundcheck. A wrong video is worse than no video.

## Directory Structure

- `audits/` — Timestamped audit results. Each audit captures match accuracy across all venues at a point in time. Never delete these — they track improvement over time.
- `corrections.json` — Log of every manual correction. This is training data for the matching algorithm.
- Future: `audit_accuracy.py`, `confidence.py` — Scripts for running audits and scoring matches.

## Related Files

- `scrapers/overrides.json` — Manual YouTube ID overrides and show-level name corrections
- `scripts/validate_shows.py` — Data validation (flags bad artist names, missing videos, etc.)
- `docs/strategy.md` — YouTube Match Accuracy plan (under Operations Backlog)
