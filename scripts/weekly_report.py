#!/usr/bin/env python3
"""
Weekly analytics report for Local Soundcheck.

Pulls GA4 data via the Google Analytics Data API, formats a readable
text report, and posts it as a GitHub Issue (triggering email notification).

Usage:
    python scripts/weekly_report.py                      # Default 7-day report → GitHub Issue
    python scripts/weekly_report.py --days 30            # Last 30 days
    python scripts/weekly_report.py --venue catscradle   # Filter to one venue
    python scripts/weekly_report.py --artist "Briscoe"   # Filter to one artist
    python scripts/weekly_report.py --output report.txt  # Write to file instead of Issue

Requires:
    - GA4_SERVICE_ACCOUNT: JSON key (env var with JSON string, or path to .json file)
    - GA4_PROPERTY_ID: GA4 property ID (numeric)
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    FilterExpression,
    Filter,
    Metric,
    OrderBy,
    RunReportRequest,
)
from google.oauth2 import service_account


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_client():
    """Build an authenticated GA4 Data API client."""
    creds_raw = os.environ.get("GA4_SERVICE_ACCOUNT", "")
    if not creds_raw:
        sys.exit("ERROR: GA4_SERVICE_ACCOUNT environment variable not set.")

    # Support both a JSON string and a file path
    if creds_raw.strip().startswith("{"):
        info = json.loads(creds_raw)
    else:
        with open(creds_raw) as f:
            info = json.load(f)

    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    return BetaAnalyticsDataClient(credentials=credentials)


def get_property_id():
    pid = os.environ.get("GA4_PROPERTY_ID", "")
    if not pid:
        sys.exit("ERROR: GA4_PROPERTY_ID environment variable not set.")
    return pid


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def run_report(client, property_id, dimensions, metrics, date_range,
               dim_filter=None, order_bys=None, limit=10):
    """Run a single GA4 report and return rows as list of dicts."""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[date_range],
        order_bys=order_bys or [],
        dimension_filter=dim_filter,
        limit=limit,
    )
    response = client.run_report(request)

    rows = []
    for row in response.rows:
        entry = {}
        for i, dim in enumerate(dimensions):
            entry[dim] = row.dimension_values[i].value
        for i, met in enumerate(metrics):
            entry[met] = row.metric_values[i].value
        rows.append(entry)
    return rows


def make_date_range(days):
    """Return a DateRange for the last N days (not including today)."""
    end = datetime.now() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    return DateRange(
        start_date=start.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d"),
    ), start, end


def make_prev_date_range(days, start):
    """Return a DateRange for the period immediately before the main range."""
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return DateRange(
        start_date=prev_start.strftime("%Y-%m-%d"),
        end_date=prev_end.strftime("%Y-%m-%d"),
    )


def venue_filter(venue_slug):
    """Build a dimension filter for customEvent:venue_name."""
    return FilterExpression(
        filter=Filter(
            field_name="customEvent:venue_name",
            string_filter=Filter.StringFilter(
                match_type=Filter.StringFilter.MatchType.CONTAINS,
                value=venue_slug,
                case_sensitive=False,
            ),
        )
    )


def artist_filter(artist_name):
    """Build a dimension filter for customEvent:artist."""
    return FilterExpression(
        filter=Filter(
            field_name="customEvent:artist",
            string_filter=Filter.StringFilter(
                match_type=Filter.StringFilter.MatchType.CONTAINS,
                value=artist_name,
                case_sensitive=False,
            ),
        )
    )


def event_filter(event_name):
    """Build a dimension filter for eventName."""
    return FilterExpression(
        filter=Filter(
            field_name="eventName",
            string_filter=Filter.StringFilter(
                match_type=Filter.StringFilter.MatchType.EXACT,
                value=event_name,
            ),
        )
    )


# ---------------------------------------------------------------------------
# Report sections
# ---------------------------------------------------------------------------

def fmt_duration(seconds_str):
    """Format seconds string to Xm Ys."""
    try:
        secs = int(float(seconds_str))
    except (ValueError, TypeError):
        return "0m 0s"
    return f"{secs // 60}m {secs % 60:02d}s"


def fmt_int(val):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def pct_change(current, previous):
    """Return a formatted percentage change string."""
    if previous == 0:
        return "+new" if current > 0 else "—"
    change = ((current - previous) / previous) * 100
    if change > 0:
        return f"+{change:.0f}%"
    elif change < 0:
        return f"{change:.0f}%"
    return "0%"


def section_overall(client, prop_id, date_range, prev_range):
    """Top-line metrics with week-over-week comparison."""
    metrics = ["totalUsers", "newUsers", "screenPageViews",
               "userEngagementDuration", "eventCount"]

    current = run_report(client, prop_id, [], metrics, date_range, limit=1)
    previous = run_report(client, prop_id, [], metrics, prev_range, limit=1)

    cur = current[0] if current else {}
    prev = previous[0] if previous else {}

    users = fmt_int(cur.get("totalUsers", 0))
    new_users = fmt_int(cur.get("newUsers", 0))
    views = fmt_int(cur.get("screenPageViews", 0))
    eng_secs = float(cur.get("userEngagementDuration", 0))
    events = fmt_int(cur.get("eventCount", 0))

    prev_users = fmt_int(prev.get("totalUsers", 0))
    prev_views = fmt_int(prev.get("screenPageViews", 0))

    avg_time = fmt_duration(str(eng_secs / users)) if users > 0 else "0m 00s"
    returning = users - new_users

    lines = [
        "OVERVIEW",
        f"  Users: {users} ({pct_change(users, prev_users)} vs prev period)  |  New: {new_users}  |  Returning: {returning}",
        f"  Page Views: {views} ({pct_change(views, prev_views)} vs prev period)  |  Avg Engagement: {avg_time}  |  Events: {events}",
    ]
    return "\n".join(lines)


def section_venues(client, prop_id, date_range):
    """Venue activity breakdown table."""
    # Get venue-level user/view/engagement data
    venue_rows = run_report(
        client, prop_id,
        dimensions=["customEvent:venue_name"],
        metrics=["totalUsers", "newUsers", "screenPageViews",
                 "userEngagementDuration"],
        date_range=date_range,
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(
            metric_name="totalUsers"), desc=True)],
        limit=20,
    )

    # Get sample_play counts per venue
    play_rows = run_report(
        client, prop_id,
        dimensions=["customEvent:venue_name"],
        metrics=["eventCount"],
        date_range=date_range,
        dim_filter=event_filter("sample_play"),
        limit=20,
    )
    plays_by_venue = {r["customEvent:venue_name"]: fmt_int(r["eventCount"])
                      for r in play_rows}

    # Get ticket_click counts per venue
    ticket_rows = run_report(
        client, prop_id,
        dimensions=["customEvent:venue_name"],
        metrics=["eventCount"],
        date_range=date_range,
        dim_filter=event_filter("ticket_click"),
        limit=20,
    )
    tickets_by_venue = {r["customEvent:venue_name"]: fmt_int(r["eventCount"])
                        for r in ticket_rows}

    # Get top artist per venue
    artist_rows = run_report(
        client, prop_id,
        dimensions=["customEvent:venue_name", "customEvent:artist"],
        metrics=["eventCount"],
        date_range=date_range,
        dim_filter=event_filter("sample_play"),
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(
            metric_name="eventCount"), desc=True)],
        limit=50,
    )
    top_artist_by_venue = {}
    for r in artist_rows:
        v = r["customEvent:venue_name"]
        if v not in top_artist_by_venue:
            name = r["customEvent:artist"]
            count = fmt_int(r["eventCount"])
            # Truncate long names
            if len(name) > 12:
                name = name[:11] + "."
            top_artist_by_venue[v] = f"{name} ({count})"

    if not venue_rows:
        return "VENUE ACTIVITY\n  No venue data for this period."

    # Build table
    header = f"{'Venue':<18}| {'Users':>5} | {'New':>3} | {'Ret':>3} | {'Views':>5} | {'Avg Time':>8} | {'Plays':>5} | {'Tix':>3} | Top Artist"
    sep = "-" * 18 + "+" + "-" * 7 + "+" + "-" * 5 + "+" + "-" * 5 + "+" + "-" * 7 + "+" + "-" * 10 + "+" + "-" * 7 + "+" + "-" * 5 + "+" + "-" * 15

    total_users = 0
    total_new = 0
    total_views = 0
    total_eng = 0
    total_plays = 0
    total_tickets = 0

    rows = []
    for r in venue_rows:
        v = r["customEvent:venue_name"]
        if not v or v == "(not set)":
            continue
        users = fmt_int(r["totalUsers"])
        new = fmt_int(r["newUsers"])
        ret = users - new
        views = fmt_int(r["screenPageViews"])
        eng = float(r.get("userEngagementDuration", 0))
        avg = fmt_duration(str(eng / users)) if users > 0 else "0m 00s"
        plays = plays_by_venue.get(v, 0)
        tix = tickets_by_venue.get(v, 0)
        top_a = top_artist_by_venue.get(v, "—")

        # Truncate venue name for display
        vname = v if len(v) <= 17 else v[:16] + "."

        total_users += users
        total_new += new
        total_views += views
        total_eng += eng
        total_plays += plays
        total_tickets += tix

        rows.append(
            f"{vname:<18}| {users:>5} | {new:>3} | {ret:>3} | {views:>5} | {avg:>8} | {plays:>5} | {tix:>3} | {top_a}"
        )

    total_avg = fmt_duration(str(total_eng / total_users)) if total_users > 0 else "0m 00s"
    total_row = f"{'TOTAL':<18}| {total_users:>5} | {total_new:>3} | {total_users - total_new:>3} | {total_views:>5} | {total_avg:>8} | {total_plays:>5} | {total_tickets:>3} |"

    lines = ["VENUE ACTIVITY", header, sep] + rows + [sep, total_row]
    return "\n".join(lines)


def section_origins(client, prop_id, date_range):
    """User origins by city."""
    rows = run_report(
        client, prop_id,
        dimensions=["city", "region"],
        metrics=["totalUsers"],
        date_range=date_range,
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(
            metric_name="totalUsers"), desc=True)],
        limit=10,
    )

    if not rows:
        return "USER ORIGINS\n  No location data for this period."

    header = f"{'City':<18}| {'State':<14}| {'Users':>5}"
    sep = "-" * 18 + "+" + "-" * 15 + "+" + "-" * 7

    lines = ["USER ORIGINS", header, sep]
    for r in rows:
        city = r["city"]
        if not city or city == "(not set)":
            continue
        region = r["region"]
        if len(region) > 13:
            region = region[:12] + "."
        users = fmt_int(r["totalUsers"])
        cname = city if len(city) <= 17 else city[:16] + "."
        lines.append(f"{cname:<18}| {region:<14}| {users:>5}")

    return "\n".join(lines)


def section_traffic(client, prop_id, date_range):
    """Traffic sources."""
    rows = run_report(
        client, prop_id,
        dimensions=["sessionSource", "sessionMedium"],
        metrics=["totalUsers"],
        date_range=date_range,
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(
            metric_name="totalUsers"), desc=True)],
        limit=10,
    )

    if not rows:
        return "TRAFFIC SOURCES\n  No traffic data for this period."

    header = f"{'Source':<18}| {'Medium':>10} | {'Users':>5}"
    sep = "-" * 18 + "+" + "-" * 12 + "+" + "-" * 7

    lines = ["TRAFFIC SOURCES", header, sep]
    for r in rows:
        src = r["sessionSource"] or "(direct)"
        med = r["sessionMedium"] or "(none)"
        users = fmt_int(r["totalUsers"])
        sname = src if len(src) <= 17 else src[:16] + "."
        mname = med if len(med) <= 10 else med[:9] + "."
        lines.append(f"{sname:<18}| {mname:>10} | {users:>5}")

    return "\n".join(lines)


def section_top_artists(client, prop_id, date_range, dim_filter=None):
    """Top artists played."""
    rows = run_report(
        client, prop_id,
        dimensions=["customEvent:artist", "customEvent:venue_name",
                     "customEvent:role"],
        metrics=["eventCount"],
        date_range=date_range,
        dim_filter=dim_filter or event_filter("sample_play"),
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(
            metric_name="eventCount"), desc=True)],
        limit=10,
    )

    if not rows:
        return "TOP ARTISTS PLAYED\n  No play data for this period."

    header = f"{'Artist':<18}| {'Plays':>5} | {'Venue':<17}| {'Role':<10}"
    sep = "-" * 18 + "+" + "-" * 7 + "+" + "-" * 17 + "+" + "-" * 10

    lines = ["TOP ARTISTS PLAYED", header, sep]
    for r in rows:
        art = r["customEvent:artist"]
        if not art or art == "(not set)":
            continue
        venue = r["customEvent:venue_name"]
        role = r["customEvent:role"]
        plays = fmt_int(r["eventCount"])
        aname = art if len(art) <= 17 else art[:16] + "."
        vname = venue if len(venue) <= 16 else venue[:15] + "."
        lines.append(f"{aname:<18}| {plays:>5} | {vname:<17}| {role:<10}")

    return "\n".join(lines)


def section_devices(client, prop_id, date_range):
    """Device breakdown."""
    rows = run_report(
        client, prop_id,
        dimensions=["deviceCategory"],
        metrics=["totalUsers"],
        date_range=date_range,
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(
            metric_name="totalUsers"), desc=True)],
        limit=5,
    )

    if not rows:
        return "DEVICE BREAKDOWN\n  No device data for this period."

    total = sum(fmt_int(r["totalUsers"]) for r in rows)

    header = f"{'Device':<12}| {'Users':>5} | {'% of Total':>10}"
    sep = "-" * 12 + "+" + "-" * 7 + "+" + "-" * 12

    lines = ["DEVICE BREAKDOWN", header, sep]
    for r in rows:
        dev = r["deviceCategory"].capitalize()
        users = fmt_int(r["totalUsers"])
        pct = (users / total * 100) if total > 0 else 0
        lines.append(f"{dev:<12}| {users:>5} | {pct:>9.1f}%")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_report(client, prop_id, days, venue=None, artist_name=None):
    """Build the full report text."""
    date_range, start, end = make_date_range(days)
    prev_range = make_prev_date_range(days, start)

    start_str = start.strftime("%b %d")
    end_str = end.strftime("%b %d, %Y")
    now_str = datetime.now().strftime("%a %b %d, %Y %I:%M %p ET")

    title = "LOCAL SOUNDCHECK — WEEKLY ANALYTICS"
    if venue:
        title += f"  [{venue}]"
    if artist_name:
        title += f"  [{artist_name}]"

    period = f"{start_str} - {end_str}  ({days} days, vs prev period)"

    # Build filter if venue or artist specified
    dim_filter = None
    if venue:
        dim_filter = venue_filter(venue)
    elif artist_name:
        dim_filter = artist_filter(artist_name)

    sections = [
        title,
        period,
        "",
        section_overall(client, prop_id, date_range, prev_range),
        "",
        section_venues(client, prop_id, date_range),
        "",
        section_origins(client, prop_id, date_range),
        "",
        section_traffic(client, prop_id, date_range),
        "",
        section_top_artists(client, prop_id, date_range),
        "",
        section_devices(client, prop_id, date_range),
        "",
        f"Generated: {now_str}",
    ]

    return "\n".join(sections)


def post_github_issue(title, body):
    """Create a GitHub Issue with the report."""
    result = subprocess.run(
        ["gh", "issue", "create",
         "--title", title,
         "--body", body,
         "--label", "weekly-report"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Failed to create GitHub Issue: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(f"Issue created: {result.stdout.strip()}")


def main():
    parser = argparse.ArgumentParser(description="Local Soundcheck weekly analytics report")
    parser.add_argument("--days", type=int, default=7, help="Number of days to report (default: 7)")
    parser.add_argument("--venue", type=str, help="Filter to a specific venue slug")
    parser.add_argument("--artist", type=str, help="Filter to a specific artist")
    parser.add_argument("--output", type=str, help="Write report to file instead of GitHub Issue")
    args = parser.parse_args()

    client = get_client()
    prop_id = get_property_id()

    report = build_report(client, prop_id, args.days,
                          venue=args.venue, artist_name=args.artist)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to {args.output}")
    else:
        # Post as GitHub Issue
        _, start, end = make_date_range(args.days)
        date_label = f"{start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
        issue_title = f"Weekly Analytics — {date_label}"

        # Wrap in code block for monospace formatting
        body = f"```\n{report}\n```"
        post_github_issue(issue_title, body)


if __name__ == "__main__":
    main()
