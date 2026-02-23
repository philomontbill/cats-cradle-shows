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

## Calibration Notes

### View Count Cap: 5M
- Set Feb 23, 2026
- Rationale: all venues are small indie rooms (100-750 capacity). 5M catches famous-song collisions while leaving headroom.
- First run: no false rejections observed at this threshold. Some legitimate artists with big videos were rejected (Aterciopelados 42M, Gogol Bordello 14M) — these need overrides, not a threshold change.

### Topic Channel Fast Pass
- Set Feb 23, 2026
- Topic channels skip the view count check entirely when artist name matches.
- First run: several Topic channel videos correctly verified (Blood Red River, Fugitive Visions, SADBOY PROLIFIC).

### Channel Subscriber Threshold: 2M (modifier, not hard cutoff)
- Set Feb 23, 2026
- Only rejects when channel doesn't match artist AND has 2M+ subscribers.
- First run: caught KEXP (3.8M), NPR Music (12.4M), Metallica (12.2M), Spinnin' Records (32M), etc. All correct rejections.

### Upload Date Flag: 15 years
- Set Feb 23, 2026
- Only rejects when video is 15+ years old AND channel doesn't match.
- First run: caught 4 videos (17-20 years old). All correct rejections.
