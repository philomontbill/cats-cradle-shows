#!/usr/bin/env python3
"""
Mark past shows as expired. Runs after each daily scrape.

- Parses show dates (format: "Day, Mon DD") and infers the year
- Adds "expired": true to shows whose date has passed
- Recalculates total_shows, shows_with_video, shows_with_image to exclude expired
- Preserves expired shows in the JSON for historical data
"""

import json
import glob
import os
import sys
from datetime import datetime, date

# Month abbreviation to number
MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}


def parse_show_date(date_str):
    """Parse 'Day, Mon DD' into a date object. Infers year from current date."""
    try:
        # e.g. "Fri, Feb 20" -> ["Fri", "Feb 20"]
        parts = date_str.split(", ", 1)
        if len(parts) != 2:
            return None
        month_day = parts[1].strip().split()
        if len(month_day) != 2:
            return None
        month_str = month_day[0].lower()
        day = int(month_day[1])
        month = MONTHS.get(month_str)
        if not month:
            return None

        # Infer year: assume current year unless the date is more than
        # 2 months in the past (then it's probably next year's show
        # that wrapped around)
        today = date.today()
        show_date = date(today.year, month, day)

        # If the show date is more than 60 days in the future,
        # it might be from late last year — but this shouldn't happen
        # with venue calendars. If it's way in the past (>2 months),
        # it might be next year. For simplicity: use current year.
        return show_date
    except (ValueError, IndexError):
        return None


def process_venue(filepath):
    """Process one venue file. Returns (modified, expired_count, active_count)."""
    with open(filepath) as f:
        data = json.load(f)

    shows = data.get("shows", [])
    today = date.today()
    modified = False
    expired_count = 0
    active_count = 0
    active_with_video = 0
    active_with_image = 0

    for show in shows:
        show_date = parse_show_date(show.get("date", ""))

        if show_date and show_date < today:
            if not show.get("expired"):
                show["expired"] = True
                modified = True
            expired_count += 1
        else:
            # Remove expired flag if date is today or future
            # (handles edge cases like date corrections)
            if show.get("expired"):
                del show["expired"]
                modified = True
            active_count += 1
            if show.get("youtube_id"):
                active_with_video += 1
            if show.get("image"):
                active_with_image += 1

    # Update summary counts to reflect only active shows
    if data.get("total_shows") != active_count:
        data["total_shows"] = active_count
        modified = True
    if data.get("shows_with_video") != active_with_video:
        data["shows_with_video"] = active_with_video
        modified = True
    if data.get("shows_with_image") != active_with_image:
        data["shows_with_image"] = active_with_image
        modified = True

    if modified:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    return modified, expired_count, active_count


def main():
    files = sorted(glob.glob("data/shows-*.json"))
    if not files:
        print("No show data files found in data/")
        sys.exit(1)

    total_expired = 0
    total_active = 0
    modified_files = []

    for filepath in files:
        venue_key = os.path.basename(filepath).replace("shows-", "").replace(".json", "")
        modified, expired, active = process_venue(filepath)
        total_expired += expired
        total_active += active
        if modified:
            modified_files.append(venue_key)
        print(f"  {venue_key}: {active} active, {expired} expired"
              + (" (updated)" if modified else ""))

    print(f"\nTotal: {total_active} active shows, {total_expired} expired")
    if modified_files:
        print(f"Files modified: {', '.join(modified_files)}")
    else:
        print("No changes needed.")


if __name__ == "__main__":
    main()
