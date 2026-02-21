#!/usr/bin/env python3
"""
Scrape monitoring script. Runs after each daily scrape.

- Compares current show counts to previous counts (stored in logs/scrape-history.json)
- Logs every run to logs/scrape-report.txt
- Prints ALERT lines for: zero shows, 50%+ drop from previous scrape
- Exit code 1 if any alerts fired (used by GitHub Actions to trigger email)
"""

import json
import glob
import os
import sys
from datetime import datetime

HISTORY_FILE = "logs/scrape-history.json"
REPORT_FILE = "logs/scrape-report.txt"
DROP_THRESHOLD = 0.5  # 50% drop triggers alert


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {}


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_current_counts():
    """Read each venue JSON and return {venue_key: show_count}."""
    counts = {}
    for filepath in sorted(glob.glob("data/shows-*.json")):
        venue_key = os.path.basename(filepath).replace("shows-", "").replace(".json", "")
        try:
            with open(filepath) as f:
                data = json.load(f)
            counts[venue_key] = len(data.get("shows", []))
        except (json.JSONDecodeError, IOError):
            counts[venue_key] = -1  # -1 signals a read/parse failure
    return counts


def check_counts(current, previous):
    """Compare current counts to previous. Return (alerts, info)."""
    alerts = []
    info = []

    for venue, count in sorted(current.items()):
        prev = previous.get(venue)

        if count == -1:
            alerts.append(f"ALERT: {venue} — failed to read/parse JSON")
        elif count == 0:
            alerts.append(f"ALERT: {venue} — zero shows returned")
        elif prev is not None and prev > 0:
            drop = (prev - count) / prev
            if drop >= DROP_THRESHOLD:
                alerts.append(
                    f"ALERT: {venue} — show count dropped {prev} → {count} "
                    f"({drop:.0%} drop)"
                )
            else:
                info.append(f"  {venue}: {count} shows (was {prev})")
        else:
            info.append(f"  {venue}: {count} shows (no previous data)")

    return alerts, info


def append_report(timestamp, alerts, info):
    """Append this run's results to the report log."""
    with open(REPORT_FILE, "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Scrape Monitor — {timestamp}\n")
        f.write(f"{'='*60}\n")
        if alerts:
            f.write(f"\n{len(alerts)} ALERT(s):\n")
            for a in alerts:
                f.write(f"  {a}\n")
        f.write(f"\nVenue Summary:\n")
        for line in info:
            f.write(f"{line}\n")
        f.write("\n")


def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    previous = load_history()
    current = get_current_counts()
    alerts, info = check_counts(current, previous)

    # Always save current counts as new history
    save_history(current)

    # Append to log file
    append_report(timestamp, alerts, info)

    # Print to stdout (visible in GitHub Actions logs)
    print(f"Scrape Monitor — {timestamp}")
    print(f"Venues checked: {len(current)}")

    if alerts:
        print(f"\n{len(alerts)} ALERT(s):")
        for a in alerts:
            print(f"  {a}")
        print("\nVenue counts:")
        for line in info:
            print(line)
        sys.exit(1)
    else:
        print("All venues healthy.")
        for line in info:
            print(line)


if __name__ == "__main__":
    main()
