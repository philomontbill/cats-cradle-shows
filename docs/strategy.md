# LOCAL SOUNDCHECK — STRATEGY

## Mission

Nothing compares to the experience of discovering a fresh talent in the intimacy of a small venue. Local Soundcheck is committed to helping you find great talent and to helping that new talent grow.

## What It Is

A venue-first music discovery tool for small and mid-size venues. Browse shows by venue, hear every band instantly via YouTube samples, buy tickets directly from the venue. No middleman, no fees, no account required.

## Why This Matters

- No one else does this. A competitive review of 15+ platforms (Bandsintown, Songkick, Spotify, DICE, Oh My Rockness, hppn.ing, and others) confirmed that no existing product combines venue-first browsing, small venue focus, and instant music samples. All major platforms are artist-first. None make the venue the entry point for discovery.
- Small venue artists are hard to find on Spotify. Common band names, openers with no streaming presence, local acts with no distribution. We solve that by curating the right sample for every band.
- Venues don't lose anything. Every ticket click goes directly to their site.

## Where We Are (Feb 19, 2026)

- Product: Working. 11 venues across 5 cities. Automated scraping via GitHub Actions.
- Users: None beyond the creator and a handful of friends.
- Budget: Zero. Sweat equity only until proof of concept.
- Team: Solo.
- Email: info@localsoundcheck.com sending and receiving through Gmail.
- Artist outreach: 13 emails sent to artists playing Cat's Cradle through March 10. 9 Instagram DMs sent. 1 response already (Briscoe — sent preferred YouTube link). 1 email bounced (Immortal Technique). 2 artists had Instagram DMs disabled.
- Reddit: Account (NC_Brady) has 12 karma, 12 contributions across 5 subreddits. First post for r/triangle drafted, ready to post next Tue-Wed.
- Instagram: @localsoundcheck account set up. Content strategy not yet started.

## Phase 1: Prove It (Triangle — Now)

Prove that people other than me find this useful. Focus entirely on the Raleigh-Durham-Chapel Hill market.

Tactics:
- Reddit: Post in r/triangle, r/chapelhill. Authentic, not promotional.
- Instagram: Share content, engage with local music community.
- Artist outreach: Contact upcoming artists. Ask if they see value. If yes, they become organic advocates.
- Track everything: Site visits, sample plays, ticket clicks, return visitors.

Success looks like: Strangers using the site regularly without being asked.

## Phase 2: Expand (After Proof)

Once proven locally, expand rapidly to other markets with active small venue scenes. The code is easy to copy — speed and market presence are the only protection.

Target markets: Cities with a concentration of small and mid-size indie venues where audiences are likely to encounter artists they don't already know.

Priority cities: TBD based on Phase 1 learnings.

### Operations That Must Scale

The following areas require defined processes before expanding beyond the Triangle. Each becomes harder to manage with every venue added.

#### 1. Data Quality & Edge Cases

Scrapers pull raw data from venue websites. That data is often messy.

Known issues:
- **Multi-artist events**: Festivals, showcases, and "Presents" events list one title but contain multiple acts. The Carrboro Bluegrass Festival was the first example — the scraper treated the event name as the artist. These need manual review or pattern detection to extract real band names.
- **Artist name normalization**: The same artist may appear as "The War on Drugs" at one venue and "War on Drugs" at another. Without normalization, video matching and deduplication break.
- **Image link rot**: Artist images sourced from venue websites can disappear or change URLs without notice.
- **Cancelled/postponed/sold-out shows**: Scrapers must detect show status changes. Stale listings (showing a cancelled show as upcoming) erode user trust fast.

Current mitigation: `validate_shows.py` catches some issues (long names, festival keywords, missing videos). Needs to expand as new edge cases surface.

#### 2. YouTube Curation

Every show needs the right video sample. This is the core of the product and the hardest thing to automate.

Challenges:
- **Volume**: More venues = more new artists per week needing videos. At 11 venues this is manageable. At 50 it won't be.
- **Wrong matches**: Common band names return wrong YouTube results. Manual verification is currently required.
- **Artist preferences**: Artists have already requested specific videos via Instagram (this started during Phase 1 outreach). Need a reliable process to receive, verify, and apply these requests.
- **Opener coverage**: Openers are harder to find on YouTube. Many have no streaming presence at all.

Process needed: Define a first-pass automation (YouTube API search by artist name) with a manual review/override step. Track artist-submitted preferences so they persist across future scrapes.

#### 3. Scraper Maintenance & Monitoring

Each venue requires a custom scraper because no two venue websites are structured the same.

Risks:
- **Site redesigns**: Venues redesign their websites without notice. A scraper that worked yesterday returns garbage today. More venues = more frequent breakage.
- **Silent failures**: GitHub Actions can fail without anyone noticing. A scrape that returns zero results or malformed data needs to trigger an alert.
- **Scrape timing**: Shows need to appear promptly after venues announce them. Stale calendars make the site feel abandoned.

Process needed: Automated monitoring that flags when a scrape returns zero shows, fewer shows than expected, or fails entirely. Daily review cadence to catch issues before users do.

#### 4. Venue Onboarding Pipeline

Adding a new venue is currently ad hoc — build a scraper, test it, deploy it.

Questions to answer:
- How long does each new scraper take to build and test?
- What's the QA checklist before a venue goes live?
- How do we prioritize which venues to add in a new city?
- Is there a standard scraper template that can be adapted, or does each one start from scratch?

#### 5. Inbound Communication Management

Three inbound channels are already active and will grow with the audience.

**Email (info@localsoundcheck.com)**:
- Artist inquiries, venue questions, user feedback, video change requests
- Currently managed through Gmail. Needs a triage process — what gets a response, how fast, and who handles it at scale.

**Instagram DMs (@localsoundcheck)**:
- Artist video link requests (already happening)
- Fan messages, venue inquiries
- Response time matters — slow replies signal an inactive project. Need a target SLA (e.g., respond within 24 hours).

**Reddit (NC_Brady)**:
- Comment replies after posting in local subreddits
- Must be available for 2+ hours after posting. Unanswered comments look bad.

Process needed: A single daily check-in that covers all three channels. Log requests that require action (video changes, outreach responses) into the spreadsheet or a tracking system.

#### 6. Daily Operations Checklist

As the above areas grow, a repeatable daily routine prevents things from falling through the cracks.

Suggested daily review:
- Check scrape results — did all venues return data? Any failures or anomalies?
- Review new shows — any festivals, multi-artist events, or missing videos that need manual attention?
- Check inbound messages — email, Instagram DMs, Reddit notifications
- Process any artist video change requests
- Update tracking spreadsheet with outreach responses and status changes

## Phase 3: Monetize (After Expansion)

Model TBD. Possible paths: venue partnerships, artist promotion tools, sponsored placement. Will not compromise the user experience or the mission.

## What We Don't Do

- Arenas, amphitheaters, stadium shows. Those fans already know the bands.
- Ticket sales. We send people directly to venues.
- Artist-first discovery. The venue is always the entry point.
