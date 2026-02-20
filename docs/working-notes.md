# Working Notes

## Current Status (Feb 19, 2026)

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
- Google Analytics tracking
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

### Chrome Extension
- Not connecting to Claude Code this session — troubleshoot next time
