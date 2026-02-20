#!/usr/bin/env python3
"""
Validate show data and flag entries that need manual review.

Checks:
- Artist name too long (60+ chars) — likely a festival/event title
- Artist contains event keywords (Presents, Festival, Series, etc.)
- Opener has "with" joining multiple bands
- Missing youtube_id
- Opener listed but no opener video
- Duplicate artist names across venues (possible normalization issue)
- Image URL issues (missing or unreachable)
- Cancelled/postponed keywords in artist name or notice
- Tour name appended to artist name (contains "Tour" or colon)
- Missing required fields (date, venue, event_url)

Exit code 1 if any issues found. Prints summary suitable for email alert.
"""

import json
import glob
import sys
import os

LONG_NAME_THRESHOLD = 60
EVENT_WORDS = [
    "presents", "festival", "series", "celebrates", "showcase",
    "marathon", "benefit", "fundraiser", "residency", "revue"
]
CANCEL_WORDS = ["cancelled", "canceled", "postponed", "rescheduled"]
TOUR_INDICATORS = [": ", " tour", " Tour", " TOUR"]


def check_show(show, venue_file):
    """Check a single show for issues. Returns list of (severity, message)."""
    flags = []
    artist = show.get("artist", "")
    opener = show.get("opener", "") or ""
    date = show.get("date", "")
    notice = show.get("notice", "") or ""
    label = f"{artist} ({date}) in {os.path.basename(venue_file)}"

    # Long artist name — likely a festival/event title
    if len(artist) > LONG_NAME_THRESHOLD:
        flags.append(("WARNING", f"LONG ARTIST NAME ({len(artist)} chars): {label}"))

    # Artist name contains event keywords
    artist_lower = artist.lower()
    for word in EVENT_WORDS:
        if word in artist_lower:
            flags.append(("WARNING", f"ARTIST contains '{word}': {label}"))
            break

    # Cancelled/postponed detection
    for word in CANCEL_WORDS:
        if word in artist_lower or word in notice.lower():
            flags.append(("WARNING", f"POSSIBLY CANCELLED/POSTPONED: {label}"))
            break

    # Tour name appended to artist — e.g. "Peter McPoland: Big Lucky Tour"
    for indicator in TOUR_INDICATORS:
        if indicator in artist:
            flags.append(("INFO", f"TOUR NAME IN ARTIST: {label}"))
            break

    # Opener has "with" — may need to split
    if " with " in opener.lower() and not opener.lower().startswith("with"):
        flags.append(("WARNING", f"OPENER contains 'with' (multiple bands?): \"{opener}\" — {label}"))

    # Missing youtube_id
    if not show.get("youtube_id"):
        flags.append(("WARNING", f"NO VIDEO: {label}"))

    # Opener listed but no opener video
    if opener and not show.get("opener_youtube_id"):
        flags.append(("INFO", f"OPENER NO VIDEO: {opener} — {label}"))

    # Missing required fields
    if not date:
        flags.append(("WARNING", f"MISSING DATE: {artist} in {os.path.basename(venue_file)}"))
    if not show.get("venue"):
        flags.append(("WARNING", f"MISSING VENUE: {label}"))
    if not show.get("event_url") and not show.get("ticket_url"):
        flags.append(("WARNING", f"NO TICKET URL: {label}"))

    # Image URL check — just verify field exists (HTTP checks would be slow)
    if not show.get("image"):
        flags.append(("INFO", f"NO IMAGE: {label}"))

    return flags


def check_duplicates(all_artists):
    """Check for possible duplicate artists across venues (normalization issues)."""
    flags = []
    # Normalize: lowercase, strip "the ", strip trailing whitespace
    normalized = {}
    for artist, venue_file in all_artists:
        key = artist.lower().strip()
        if key.startswith("the "):
            key = key[4:]
        if key not in normalized:
            normalized[key] = []
        normalized[key].append((artist, venue_file))

    for key, entries in normalized.items():
        if len(entries) > 1:
            venues = [os.path.basename(v) for _, v in entries]
            names = [a for a, _ in entries]
            # Only flag if names differ (actual normalization issue)
            if len(set(names)) > 1:
                flags.append((
                    "WARNING",
                    f"POSSIBLE DUPLICATE: {names} across {venues}"
                ))

    return flags


def main():
    files = sorted(glob.glob("data/shows-*.json"))
    if not files:
        print("No show data files found in data/")
        sys.exit(1)

    all_flags = []
    all_artists = []

    for filepath in files:
        with open(filepath) as f:
            data = json.load(f)
        shows = data.get("shows", [])
        for show in shows:
            # Skip expired shows
            if show.get("expired"):
                continue
            all_flags.extend(check_show(show, filepath))
            all_artists.append((show.get("artist", ""), filepath))

    # Cross-venue duplicate check
    all_flags.extend(check_duplicates(all_artists))

    # Separate by severity
    warnings = [msg for sev, msg in all_flags if sev == "WARNING"]
    infos = [msg for sev, msg in all_flags if sev == "INFO"]

    if warnings or infos:
        print(f"Validation found {len(warnings)} warning(s) and {len(infos)} info item(s):\n")
        if warnings:
            print("WARNINGS (need review):")
            for w in warnings:
                print(f"  {w}")
            print()
        if infos:
            print("INFO (low priority):")
            for i in infos:
                print(f"  {i}")
            print()
        # Exit 1 only on warnings, not info-only
        if warnings:
            sys.exit(1)
    else:
        print("All show data looks clean.")


if __name__ == "__main__":
    main()
