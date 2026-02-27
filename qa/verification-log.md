# Video Verification Log

Running record of verification runs, findings, and calibration decisions. Each entry documents what happened, what we learned, and any threshold adjustments.

For the design spec (rules, thresholds, reasoning), see `qa/video-matching-logic.md`.
For verification state data, see `qa/video_states.json`.

---

## Run 1 — Feb 23, 2026 (First Run)

**Context:** First-ever verification pass. All existing video assignments were unverified. This run established the baseline.

**Results:**
- 285 videos verified (passed all checks)
- 40 videos rejected (nulled out in show data)
- 11 already verified (from overrides system)
- 3 overrides skipped (locked)
- ~650 API quota units used (6.5% of daily budget)

**Rejections by category:**

*View count exceeds 5M cap (23 rejections):*
- Bryce Vine — 98.7M views (Bowery + El Club, rejected at both)
- Alien Ant Farm / Skating Polly bill — 382M views ("Smooth Criminal" match)
- yung kai — 247M views (The Social)
- Aterciopelados — 42M views (Cat's Cradle)
- Gogol Bordello — 14.3M views (Mohawk)
- Honest Mistakes — 20.8M views (Bowery, also 17 years old)
- ALESANA — 12.7M views (Motorco, also 19 years old)
- LUEWWD XX — 88.5M views (Motorco, also 17 years old)
- Borgeous — 22.9M views + Spinnin' Records channel with 32M subs (Elevation 27)
- Kxllswxtch — 20.7M views (Kings)
- Ezra — 17.3M views + ABS-CBN channel with 10.2M subs (Kings)
- Dream, Ivory — 13.9M views (Local 506)
- Snowblinder and Dead Halos — 6.6M views (Local 506)
- Love Letter — 7.4M views (Local 506)
- LETDOWN — 17.2M views (The Social)
- DANCE — 20.5M views (The Social)
- POWFU — 8.2M views (Motorco)
- SKIZZY MARS — 12.2M views (Motorco)
- DISCO, ALWAYS — 7.6M views (Motorco)
- The Band Of Heathens — 7.3M views (Lincoln)
- Lil Texas — 9.8M views + 16 years old (Elevation 27)
- @ Kings — 21.9M views (Lincoln)
- Unplugged Sets / TRL — 5.0M views (Mohawk, barely over cap)

*Non-matching channel with 2M+ subscribers (8 rejections):*
- An Evening With — matched "Playing For Change" channel (3.5M subs)
- The Barr Brothers — matched KEXP channel (3.8M subs)
- Silk Road presents Stunna Pt 2 — matched CGTN channel (5.0M subs)
- The Four Horsemen — matched Metallica channel (12.2M subs)
- Buffalo Nichols — matched NPR Music channel (12.4M subs)
- Burning Witches — matched Nuclear Blast Records (3.4M subs)
- Mint Field — matched KEXP (3.8M subs)
- Death Lens — matched Epitaph Records (3.9M subs)

*Venue placeholder image (2 rejections):*
- Rivalry Night — Cat's Cradle Back Room, cradlevenue.png placeholder
- Dialtone/Red Kanoo/Weekend Therapy/Jackson Slater — same show, same placeholder

*Old video + no channel match (4 rejections):*
- special guest Bobcat Goldthwait — 19 years old
- Ike Reilly Assassination — 16 years old
- The Cast Of Beatlemania — 19 years old
- Music For The Masses — 20 years old + Nuclear Blast channel

*Combined (view count + age + channel, 3 rejections):*
- Oof Fighters — matched actual Foo Fighters channel (6M views, 4.2M subs, 15 years old)
- Caroline Jones — 9.5M views (Bowery)
- Lil Texas — 9.8M views + 16 years old (Elevation 27)

**Notable correct rejections:**
- Oof Fighters → Foo Fighters (tribute band matched the real band's channel)
- Alien Ant Farm → "Smooth Criminal" (382M views — most viewed rejection)
- Ezra → Filipino music channel (small venue band matched ABS-CBN Star Music)
- Borgeous → Spinnin' Records with 32M subscribers
- Rivalry Night → caught by venue placeholder image before any API call

**Observations:**
1. The 5M view cap is working well. No obvious false rejections — every rejection over 5M was clearly a wrong match or a major-label video.
2. The channel subscriber threshold (2M+) caught label/media channels effectively: KEXP, NPR Music, Metallica, Epitaph, Nuclear Blast, Spinnin' Records.
3. Venue placeholder image check caught the Rivalry Night event (not a band).
4. Upload date check caught 4 very old videos (15-20 years) that had no channel match.
5. Some rejections are bands that ARE playing these venues but matched wrong videos (e.g., Aterciopelados is real but matched a 42M-view video). These could be overridden if we find the right video.

**False rejections to investigate:**
- Aterciopelados (Cat's Cradle, Mar 10) — legitimate Colombian rock band playing CC. 42M views is real for them. May need an override with a different (lower-view) video, or a manual override accepting this one.
- Caroline Jones (Bowery, Mar 5) — may be the real artist. 9.5M views possible for a Nashville act at Bowery.
- POWFU (Motorco, Apr 11) — internet-famous artist, 8.2M views plausible. May need override.
- Gogol Bordello (Mohawk, Mar 12) — well-known band, 14.3M views is real. Override candidate.

**Thresholds seem right. No changes needed yet.** The daily report will surface any new false rejections as they come in. We'll calibrate after a week of data.

---

## Run 2 — Feb 24, 2026 (First Post-Fix Nightly)

**Context:** First nightly run after the `base_scraper.py` NameError fix (Feb 23). The fix repaired `_search_youtube_api()` so confidence scoring actually executes for API searches. Before the fix, all API searches silently failed and fell back to unscored web scraping.

**Results (audit snapshot):**
- 355 total entries, 285 with video, 70 no video
- Accuracy: 96.8%, avg confidence: 87.2

**Observations:**
- Stable accuracy from Run 1. The NameError fix didn't break existing matches — it only affects new searches going forward.
- No new threshold changes needed.

---

## Run 3 — Feb 25, 2026 (Stable Nightly)

**Context:** Routine nightly run. 10 venues (6 Triangle NC + FL, MI, NY, TX, VA).

**Results (audit snapshot):**
- 348 total entries, 295 with video, 53 no video
- Accuracy: 96.6%, avg confidence: 87.2

**Observations:**
- Show count dropped from 355 to 348 — expired shows removed, new shows added.
- Video coverage improved (285 → 295 with video, 70 → 53 no video) — the fixed scraper is finding more correct matches.
- Accuracy held steady at 96.6%.

---

## Run 4 — Feb 26, 2026 (New Venues Added)

**Context:** Two new venues added Feb 25: Neighborhood Theatre (Charlotte) and The Orange Peel (Asheville). Also deployed three verifier enhancements: trusted label allowlist (14 labels), VEVO channel detection, and Spotify-aware tiered view caps. Total venues: 13 across 6 states.

**Results (audit snapshot, AM run):**
- 407 total entries (+59 from new venues), 289 with video, 118 no video
- Accuracy: 96.5%, avg confidence: 86.9

**Key finding — YouTube API quota exhaustion:**
- Show count jumped 17% (348 → 407) with the two new venues.
- New venues have low smart-search reuse (Neighborhood Theatre ~41%, Orange Peel ~52%) vs. established venues (75-90%).
- Scrapers consumed ~9,700 of 10,000 daily API quota units (97 searches x 100 units each).
- Verifier ran after scrapers with near-zero quota remaining — got 403 (quota exhausted) on most API calls.
- Most new videos from Orange Peel and Neighborhood Theatre could not be verified, showing as "no preview."
- This created a cascading failure: rejected videos get youtube_id nulled → scrapers re-search next night → more quota burned.

**Verifier enhancements deployed (not yet fully exercised due to quota issue):**
- Trusted labels: Nuclear Blast, Epitaph, Fueled By Ramen, Spinnin', Secret City, Innovative Leisure, SideOneDummy, Rise, Fearless, Century Media, New West, Flightless, Warner, Carpark
- VEVO detection: normalized channel name ending with "vevo" gets same trust as labels
- Spotify-aware caps: popularity >= 70 → no cap, >= 50 → 50M, >= 30 → 10M, < 30 → 5M default

---

## Run 5 — Feb 26, 2026 (Manual Re-run + Rate Limiting)

**Context:** Pushed rate limiting fix (1s delay between verifications, retry logic for 429/503, status code logging). Triggered manual pipeline re-run.

**Results (audit snapshot, PM run):**
- 409 total entries, 302 with video, 107 no video
- Accuracy: 98.3%, avg confidence: 88.3

**Observations:**
- Manual re-run recovered some videos (289 → 302 with video).
- Accuracy jumped from 96.5% to 98.3% — the recovered videos were good matches.
- Still 107 no-video entries due to continued quota exhaustion (403 errors).
- Status code logging confirmed the root cause: all failures are 403 (quota exhausted), not 429 (rate limited).
- The delay and retry logic works correctly but cannot fix quota exhaustion — 403 is not retryable.

---

## Run 6 — Feb 27, 2026 (Nightly)

**Context:** First full nightly run with rate limiting code. Quota exhaustion still active — scrapers consume ~97 searches before verifier runs.

**Status:** Quota fix pending. Need to either separate API keys (scraper vs. verifier) or reduce scraper search volume.

---

## Calibration Notes

### View Count Caps (Tiered System)

*Updated Feb 25, 2026 (originally set Feb 23)*

| Condition | Cap | Rationale |
|-----------|-----|-----------|
| Default (no Spotify data or popularity < 30) | 5M | Small indie venues, 100-750 capacity |
| Spotify popularity >= 30 | 10M | Established indie artist |
| Spotify popularity >= 50 | 50M | Mid-tier artist with real streaming numbers |
| Spotify popularity >= 70 | No cap | Major artist — high views are expected |
| Trusted label channel | 50M | Known label, video is legitimate even if high views |
| VEVO channel | 50M | Same trust as labels |
| Topic channel (artist name match) | No cap | YouTube itself confirmed the artist identity |

### Trusted Labels (14)
- Set Feb 25, 2026
- Nuclear Blast, Epitaph, Fueled By Ramen, Spinnin', Secret City, Innovative Leisure, SideOneDummy, Rise, Fearless, Century Media, New West, Flightless, Warner, Carpark
- Bypass: channel mismatch, upload age, Spotify no_match rejections
- EMPIRE removed — "empire" too generic as normalized key, risk of false positives

### VEVO Channel Detection
- Set Feb 25, 2026
- Normalized channel name ending with "vevo" = trusted
- Same bypasses as trusted labels

### Spotify Identity Signals
- Set Feb 25, 2026
- Spotify `no_match` + channel doesn't match artist → reject
- Spotify `close`/`partial` match + channel mismatch → warn (not reject)
- Spotify data loaded from `qa/spotify_cache.json` (30-day TTL)

### Channel Subscriber Threshold: 2M
- Set Feb 23, 2026
- Only rejects when channel doesn't match artist AND has 2M+ subscribers
- Trusted labels and VEVO channels bypass this check

### Upload Date Flag: 15 years
- Set Feb 23, 2026
- Only rejects when video is 15+ years old AND channel doesn't match
- Trusted labels and VEVO channels bypass this check

### Venue Placeholder Image
- Set Feb 23, 2026
- Flags shows using venue default artwork (e.g., `cradlevenue.png`)
- Free check — no API call needed

---

## Known Issues

### YouTube API Quota Exhaustion (discovered Feb 26-27, 2026)
- Scrapers consume ~9,700 of 10,000 daily quota units before verifier runs
- Verifier gets 403 errors on all API calls — cannot verify new videos
- Creates cascading failure: rejected → null → re-search → more quota burned
- Fix in progress: separate API key for verifier + smarter scraper search filtering
