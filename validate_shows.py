#!/usr/bin/env python3
"""Validate show data and flag odd entries that may need manual review."""

import json
import glob
import sys

LONG_NAME_THRESHOLD = 60
SUSPECT_WORDS = ["presents", "festival", "series", "celebrates", "showcase", "marathon"]

def check_show(show, venue_file):
    flags = []
    artist = show.get("artist", "")
    opener = show.get("opener", "") or ""
    date = show.get("date", "")
    label = f"{artist} ({date}) in {venue_file}"

    # Long artist name — likely a festival/event title, not a band
    if len(artist) > LONG_NAME_THRESHOLD:
        flags.append(f"  LONG ARTIST NAME ({len(artist)} chars): {label}")

    # Artist name contains promotional words
    for word in SUSPECT_WORDS:
        if word in artist.lower():
            flags.append(f"  ARTIST contains '{word}': {label}")
            break

    # Opener has "with" — may need to split into artist/opener
    if " with " in opener.lower() and not opener.lower().startswith("with"):
        flags.append(f"  OPENER contains 'with' (multiple bands?): \"{opener}\" — {label}")

    # Missing youtube_id
    if not show.get("youtube_id"):
        flags.append(f"  NO VIDEO: {label}")

    # Opener listed but no opener video
    if opener and not show.get("opener_youtube_id"):
        flags.append(f"  OPENER NO VIDEO: {opener} — {label}")

    return flags


def main():
    files = sorted(glob.glob("data/shows-*.json"))
    if not files:
        print("No show data files found in data/")
        sys.exit(1)

    all_flags = []
    for filepath in files:
        with open(filepath) as f:
            data = json.load(f)
        shows = data.get("shows", [])
        for show in shows:
            all_flags.extend(check_show(show, filepath))

    if all_flags:
        print(f"Found {len(all_flags)} item(s) to review:\n")
        for flag in all_flags:
            print(flag)
        print()
        sys.exit(1)
    else:
        print("All show data looks clean.")


if __name__ == "__main__":
    main()
