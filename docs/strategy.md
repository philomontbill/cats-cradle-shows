# LOCAL SOUNDCHECK — STRATEGY

## Mission

Nothing compares to the experience of discovering a fresh talent in the intimacy of a small venue. Local Soundcheck is committed to helping you find great talent and to helping that new talent grow.

## What It Is

A venue-first music discovery tool for small and mid-size venues. Browse shows by venue, hear every band instantly via YouTube samples, buy tickets directly from the venue. No middleman, no fees, no account required.

## Why This Matters

- No one else does this. A competitive review of 15+ platforms (Bandsintown, Songkick, Spotify, DICE, Oh My Rockness, hppn.ing, and others) confirmed that no existing product combines venue-first browsing, small venue focus, and instant music samples. All major platforms are artist-first. None make the venue the entry point for discovery.
- Small venue artists are hard to find on Spotify. Common band names, openers with no streaming presence, local acts with no distribution. We solve that by curating the right sample for every band.
- Venues don't lose anything. Every ticket click goes directly to their site.

## Where We Are (Feb 26, 2026)

- Product: Working. 13 venues across 6 states, 8 regions. Automated nightly scraping, video verification, and Spotify enrichment via GitHub Actions.
- Video accuracy: 96.5% with automated 4-phase pipeline (scrape → Spotify enrich → verify → report). 47 manual overrides. Daily accuracy tracking in place.
- Users: None beyond the creator and a handful of friends.
- Budget: Zero. Sweat equity only until proof of concept.
- Team: Solo.
- Email: info@localsoundcheck.com sending and receiving through Gmail.
- Artist outreach: 13 emails sent to artists playing Cat's Cradle through March 10. 9 Instagram DMs sent. 1 response already (Briscoe — sent preferred YouTube link). 1 email bounced (Immortal Technique). 2 artists had Instagram DMs disabled.
- Reddit: Account (NC_Brady) has 12 karma, 12 contributions across 5 subreddits. First post for r/triangle drafted, ready to post next Tue-Wed.
- Instagram: @localsoundcheck account set up. Content strategy not yet started.
- Analytics: GA4 with custom dimensions (artist, venue, role). Weekly automated report. Search Console linked.

## Strategic Shift: Coverage as Moat (Feb 26, 2026)

The original plan was strictly sequential: prove demand in the Triangle, then expand. Experience has revealed a reason to run expansion in parallel with local validation.

**The problem:** A visitor to the site could see the concept as a cool idea that's easy to duplicate. Scrape some venue sites, match YouTube videos, done — ship it in a weekend. A well-funded team could spin up scrapers for 50 cities quickly.

**What they can't see:** The video matching pipeline took months to build. Multi-signal YouTube scoring, Spotify identity verification, trusted label detection, VEVO channel handling, tiered view count caps, oEmbed verification, manual override system, artist name cleaning for 20+ edge cases. A competitor could copy the concept overnight but replicating the quality pipeline would take months of the same iteration.

**What they can see:** How many venues the site covers. If someone lands on the site and sees only 6 Triangle venues, the reaction is "hobby project — I could do this better." If they see their own city's iconic venue alongside 20 others coast to coast, the reaction is "they've already done the work."

**The revised approach:**
- **Triangle remains the marketing focus.** That's where Reddit presence, Instagram engagement, and local credibility will generate the first real users.
- **Venue expansion runs in parallel** — not for those users, but for the moat. When a Triangle user shares the site with a friend in DC, that friend sees 9:30 Club. That's a fundamentally different first impression.
- **Don't market new cities yet.** Just have them there. Depth comes after breadth signals are in place.

The moat has two layers:
1. **Visible moat** — venue coverage breadth. Signals ambition and execution to casual observers.
2. **Invisible moat** — the quality pipeline. 96.5% accuracy, Spotify enrichment, 47 manual overrides, compounding correction data. Nearly impossible to replicate quickly, even with capital.

## Phase 1: Prove It + Build Coverage (Now)

Two tracks running simultaneously:

### Track A: Validate Demand (Triangle)

Prove that people other than me find this useful. Focus marketing entirely on the Raleigh-Durham-Chapel Hill market.

Tactics:
- Reddit: Post in r/triangle, r/chapelhill. Authentic, not promotional.
- Instagram: Share content, engage with local music community.
- Artist outreach: Contact upcoming artists. Ask if they see value. If yes, they become organic advocates.
- Track everything: Site visits, sample plays, ticket clicks, return visitors.

Success looks like: Strangers using the site regularly without being asked.

### Track B: Expand Coverage (National)

Add iconic venues in key markets to build visible breadth. Target venues that music-obsessed people in each city would immediately recognize.

**Expansion Roadmap (8 venues confirmed, feasibility verified):**

| Priority | Venue | City | State | Ticketing | Scraper Pattern |
|----------|-------|------|-------|-----------|-----------------|
| 1 | Mercury Lounge | NYC | NY | Ticketmaster | Same platform as Bowery Ballroom — reuse scraper |
| 2 | 9:30 Club | Washington | DC | Ticketmaster | WordPress, server-side, eb_calendar shortcode |
| 3 | First Avenue | Minneapolis | MN | AXS | WordPress, server-side, heading-based structure |
| 4 | The Troubadour | Los Angeles | CA | SeeTickets | WordPress + SeeTickets widget, server-side |
| 5 | Pearl St. Warehouse | Washington | DC | Tixr/Ticketweb | Webflow, server-side, clean card structure |
| 6 | Milkboy | Philadelphia | PA | Tixr | WordPress, JSON-LD structured data — cleanest scrape |
| 7 | The Basement East | Nashville | TN | TicketWeb | WordPress + tw- calendar plugin |
| 8 | Cannery Hall | Nashville | TN | AXS | WordPress, server-side, 3 stages |

All 8 are buildable with the current stack (requests + BeautifulSoup). No new dependencies required.

**After expansion:** 21 venues across 10 states — NC, NY, MI, VA, TX, FL, DC, CA, MN, PA, TN.

**Cities needing replacement venues (deferred):**
- **Los Angeles** — The Echo rejected (Live Nation Next.js/React, requires headless browser). Need a second LA venue with server-side rendered events.
- **Brooklyn** — Baby's All Right rejected (Squarespace with no on-site events, external SeeTickets returns 403). Need a Brooklyn venue with scrapeable calendar.
- **Portland** — Doug Fir Lounge closed and relocating. Revisit when reopened, or find alternative Portland venue.

### Venue Selection Criteria

When evaluating new venues:
1. **Recognition** — Would a music fan in that city immediately know the name?
2. **Capacity** — Under ~1,000 preferred. Up to ~1,500 for iconic rooms. No arenas.
3. **Independence** — Independently owned/operated preferred. Live Nation venues avoided (bigger acts, less discovery value).
4. **Scrapeability** — Server-side rendered events page, parseable with requests + BeautifulSoup. No headless browser dependencies.
5. **Ticketing** — Any platform acceptable (Ticketmaster, AXS, SeeTickets, Tixr, Eventbrite, ETIX). Direct venue links preferred.

## Phase 2: Deepen + Grow (After Proof)

Once demand is validated in the Triangle:
- Market the expanded coverage in each city (subreddit posts, local outreach)
- Add 2-3 venues per city to create depth (one iconic venue per city looks intentional; three makes it feel covered)
- Fill replacement venues for LA, Brooklyn, Portland
- Begin artist outreach in new markets

## Phase 3: Monetize (After Expansion)

Model TBD. Possible paths: venue partnerships, artist promotion tools, sponsored placement. Will not compromise the user experience or the mission.

## The Matching Algorithm Moat

### Where We Started (Feb 19, 2026)

No accuracy measurement, no systematic improvement. YouTube searches grabbed the first result. Wrong videos for common band names. No way to tell good matches from bad.

### Where We Are (Feb 26, 2026)

**96.5% accuracy** with an automated 4-phase pipeline:

1. **Scraper** — YouTube Data API search with multi-signal scoring: channel name match, view count, music category, video title, channel verification. Confidence tiers: auto-accept (>=70), flag (40-69), skip (<40). Smart search filtering preserves API quota by skipping known good matches.

2. **Spotify Enrichment** — Confirms artist identity via Spotify search. Caches popularity, genres, followers. Three match tiers (exact/close/partial). Catches non-music events, single-word collisions, and generic names.

3. **Video Verifier** — Checks unverified candidates against: tiered view count caps (Spotify popularity-aware), channel subscriber analysis, upload age, VEVO detection, trusted label allowlist (14 labels), venue placeholder images, Topic channel matching. Promotes or rejects.

4. **Daily Report** — GitHub Issue with markdown summary (tonight's delta, full inventory, accuracy tracking) + committed CSV with per-show detail.

**What's been built:**
- Multi-signal YouTube scoring with confidence tiers
- Spotify cross-reference verification
- Name disambiguation and artist name cleaning (20+ edge case patterns)
- 14 trusted labels + VEVO channel detection
- Tiered view count caps based on Spotify popularity
- Manual override system (47 overrides, 3 sections: artist, opener, show)
- Correction feedback loop via match log and accuracy history
- Automated accuracy auditing with day-over-day and 7-day trend tracking
- Validation baseline that only alerts on new warnings

**What's still ahead:**
- Channel verification badge detection (YouTube checkmark)
- Automatic weight tuning from correction history
- ML pipeline if data volume justifies it

### Why This Is Hard to Copy

Every manual correction, every artist-submitted preference, every override becomes calibration data. The matching gets better the longer it runs. A competitor starting fresh would face the same months of edge cases: "DISCO, ALWAYS" is a Harry Styles dance night, not a band. "Heated" matches H.E.A.T, not the DJ night. "Nothing" matches Whitney Houston. "Model/Actriz" is one band, not two. "Beauty School Dropout Presents: Where Did All The Butterflies Go?" is a band called Beauty School Dropout. These corrections compound into an advantage that money alone can't buy.

## Operations

### What's Built

- **Nightly pipeline** (GitHub Actions, 11 PM ET): scrapers → expire → monitor → validate → Spotify enrich → verify videos → audit → commit. All steps use continue-on-error. Alert issue on any failure.
- **Scrape monitoring**: Automated alerts via GitHub Issues (label: scrape-alert). Reports on all 14 pipeline steps.
- **Validation baseline**: `qa/validation_baseline.json` tracks known warnings. Only new warnings trigger alerts. Scales with venue growth.
- **Daily video report**: Markdown summary issue (tonight's delta + full inventory + accuracy) plus committed CSV with Changed column for filtering.
- **Weekly analytics report**: GA4 data via Analytics Data API, posted as GitHub Issue every Monday.
- **Override system**: `scrapers/overrides.json` with artist_youtube, opener_youtube, and show_overrides sections.

### What Scales With Venue Growth

- Base scraper class handles YouTube search, scoring, and name cleaning — new scrapers inherit it
- Common scraper patterns identified: Ticketmaster widget (tw- classes), eventWrapper/RHP, SeeTickets widget, JSON-LD, AXS, TicketWeb calendar
- Adding a venue = write scraper + add to venues.json + add to workflow. Typically 1 session per venue.
- Video verification pipeline processes all venues automatically — no per-venue configuration
- Spotify enrichment runs across all artists regardless of venue

### Venue Onboarding Checklist

1. Scout venue website — confirm server-side rendering, identify ticketing platform and HTML structure
2. Write scraper extending base_scraper.py — must use `process_shows_with_youtube()` (not direct `get_youtube_id()` calls)
3. Test the new scraper alone — verify artist names, dates, ticket links, images, openers parse correctly
4. **Run all scrapers locally** — confirm new scraper works alongside existing ones, check total API call count, verify no scraper bypasses shared search/rejection filtering
5. **Run the verifier locally** — confirm new venue's videos get verified (not all rejected due to quota or errors) and appear correctly in the report
6. Add venue to `data/venues.json` (state → region → venue hierarchy)
7. Add scraper step to `scrape.yml` workflow
8. Run first nightly cycle — review video report for new venue's matches
9. Add manual overrides for any edge cases (event names, common word collisions)

### Inbound Communication

Three channels active:

- **Email** (info@localsoundcheck.com): Artist inquiries, venue questions, user feedback, video change requests. Managed through Gmail.
- **Instagram** (@localsoundcheck): Artist video link requests (already happening). Target SLA: respond within 24 hours.
- **Reddit** (NC_Brady): Comment replies after local subreddit posts. Must be available 2+ hours after posting.

## What We Don't Do

- Arenas, amphitheaters, stadium shows. Those fans already know the bands.
- Ticket sales. We send people directly to venues.
- Artist-first discovery. The venue is always the entry point.
- Live Nation venues. Their acts are too big for our discovery mission.
