#!/usr/bin/env python3
"""
Weekly QC Report — Video matching quality summary.

Runs weekly (alongside the analytics report) and summarizes:
- Accuracy trend for the week (daily snapshots)
- Inventory changes (start of week vs end of week)
- Total verified/rejected/recovered for the week
- Top rejection reasons
- Sends email + appends to Google Sheets

Usage:
    python scripts/weekly_qc_report.py                  # Email + Sheets + GitHub Issue
    python scripts/weekly_qc_report.py --output report.md  # Write to file instead
    python scripts/weekly_qc_report.py --days 14        # Look back 14 days
"""

import argparse
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from scripts.report_delivery import (
    send_email, append_to_sheet, markdown_to_html, wrap_html_email,
)


def load_accuracy_history():
    """Load accuracy history from qa/accuracy_history.json."""
    path = os.path.join(_PROJECT_ROOT, "qa", "accuracy_history.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def load_video_states():
    """Load current video states."""
    path = os.path.join(_PROJECT_ROOT, "qa", "video_states.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_week_csvs(days):
    """Load daily video report CSVs from the past N days."""
    qa_dir = os.path.join(_PROJECT_ROOT, "qa")
    cutoff = datetime.now() - timedelta(days=days)
    rows = []
    for filename in sorted(os.listdir(qa_dir)):
        if not filename.startswith("video-report-") or not filename.endswith(".csv"):
            continue
        # Extract date from filename: video-report-2026-02-27.csv
        date_str = filename.replace("video-report-", "").replace(".csv", "")
        try:
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue
        if file_date < cutoff:
            continue
        filepath = os.path.join(qa_dir, filename)
        try:
            with open(filepath) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    row["_report_date"] = date_str
                    rows.append(row)
        except Exception:
            continue
    return rows


def build_report(days=7):
    """Build the weekly QC report as markdown."""
    history = load_accuracy_history()
    states = load_video_states()
    csv_rows = load_week_csvs(days)

    cutoff = datetime.now() - timedelta(days=days)
    end_date = datetime.now().strftime("%b %d, %Y")
    start_date = cutoff.strftime("%b %d")

    lines = [f"# Weekly QC Report — {start_date} to {end_date}", ""]

    # --- Section 1: Accuracy Trend ---
    week_entries = []
    for entry in history:
        try:
            d = datetime.strptime(entry["date"], "%Y-%m-%d")
            if d >= cutoff:
                week_entries.append(entry)
        except (ValueError, KeyError):
            continue

    lines.append("## Accuracy Trend")
    if week_entries:
        lines.append("| Date | Accuracy | Headliner | Opener | Avg Confidence | Verified | Rejected | Total |")
        lines.append("|------|----------|-----------|--------|---------------|----------|----------|-------|")
        for e in week_entries:
            hl_acc = e.get("headliner_accuracy", "—")
            op_acc = e.get("opener_accuracy", "—")
            hl_str = f"{hl_acc}%" if hl_acc != "—" else "—"
            op_str = f"{op_acc}%" if op_acc != "—" else "—"
            lines.append(
                f"| {e['date']} | {e.get('accuracy_rate', '—')}% "
                f"| {hl_str} | {op_str} "
                f"| {e.get('avg_confidence', '—')} "
                f"| {e.get('verified', '—')} "
                f"| {e.get('rejected', '—')} "
                f"| {e.get('total_shows', '—')} |"
            )

        # Week-over-week comparison
        if len(week_entries) >= 2:
            first = week_entries[0]
            last = week_entries[-1]
            acc_start = first.get("accuracy_rate", 0)
            acc_end = last.get("accuracy_rate", 0)
            acc_delta = acc_end - acc_start
            sign = "+" if acc_delta >= 0 else ""

            ver_start = first.get("verified", 0)
            ver_end = last.get("verified", 0)
            ver_delta = ver_end - ver_start

            rej_start = first.get("rejected", 0)
            rej_end = last.get("rejected", 0)
            rej_delta = rej_end - rej_start

            # Role deltas (graceful for older entries without role data)
            hl_start = first.get("headliner_accuracy", 0) or 0
            hl_end = last.get("headliner_accuracy", 0) or 0
            op_start = first.get("opener_accuracy", 0) or 0
            op_end = last.get("opener_accuracy", 0) or 0

            lines.append("")
            delta_parts = [f"Accuracy {sign}{acc_delta:.1f}%"]
            if hl_end:
                hl_sign = "+" if (hl_end - hl_start) >= 0 else ""
                delta_parts.append(f"Headliner {hl_sign}{hl_end - hl_start:.1f}%")
            if op_end:
                op_sign = "+" if (op_end - op_start) >= 0 else ""
                delta_parts.append(f"Opener {op_sign}{op_end - op_start:.1f}%")
            delta_parts.extend([f"Verified {ver_delta:+d}", f"Rejected {rej_delta:+d}"])
            lines.append(f"**Week delta:** {' | '.join(delta_parts)}")
    else:
        lines.append("No accuracy data for this period.")
    lines.append("")

    # --- Section 2: Current Inventory ---
    lines.append("## Current Inventory")
    status_counts = Counter()
    for artist, state in states.items():
        status = state.get("status", "unknown")
        status_counts[status] += 1

    total = sum(status_counts.values())
    if total > 0:
        lines.append("| Status | Count | % |")
        lines.append("|--------|------:|----:|")
        for status_key, label in [("verified", "Verified"),
                                   ("rejected", "Rejected"),
                                   ("override_null", "Override (null)"),
                                   ("unverified", "Unverified")]:
            count = status_counts.get(status_key, 0)
            pct = round(count / total * 100) if total else 0
            if count > 0:
                lines.append(f"| {label} | {count} | {pct}% |")
        lines.append(f"| **Total** | **{total}** | |")
    else:
        lines.append("No video states found.")
    lines.append("")

    # --- Section 3: This Week's Activity ---
    lines.append("## This Week's Activity")
    verified_rows = [r for r in csv_rows if r.get("Section") == "Verified"]
    rejected_rows = [r for r in csv_rows if r.get("Section") == "Rejected"]
    recovered_rows = [r for r in csv_rows if r.get("Changed") == "Recovered"]

    lines.append(f"**{len(verified_rows)} verified | {len(rejected_rows)} rejected | {len(recovered_rows)} recovered** (from daily reports)")
    lines.append("")

    # --- Section 4: Top Rejection Reasons ---
    lines.append("## Top Rejection Reasons")
    if rejected_rows:
        reason_counts = Counter()
        for r in rejected_rows:
            detail = r.get("Detail", "")
            # Split compound reasons
            for reason in detail.split("; "):
                reason = reason.strip()
                if reason:
                    # Normalize: strip specifics like view counts
                    if "view count" in reason and "exceeds" in reason:
                        reason = "view count exceeds cap"
                    elif "non-matching channel" in reason:
                        reason = "non-matching channel (high subscribers)"
                    elif "could not fetch" in reason:
                        reason = "could not fetch video metadata"
                    elif "not found on Spotify" in reason:
                        reason = "not found on Spotify + channel mismatch"
                    elif "years old" in reason:
                        reason = "video too old + no channel match"
                    reason_counts[reason] += 1

        lines.append("| Reason | Count |")
        lines.append("|--------|------:|")
        for reason, count in reason_counts.most_common(10):
            lines.append(f"| {reason} | {count} |")
    else:
        lines.append("No rejections this period.")
    lines.append("")

    # --- Section 5: Rejections by Venue ---
    lines.append("## Rejections by Venue")
    if rejected_rows:
        venue_counts = Counter()
        for r in rejected_rows:
            venue_counts[r.get("Venue", "Unknown")] += 1

        lines.append("| Venue | Rejected |")
        lines.append("|-------|--------:|")
        for venue, count in venue_counts.most_common():
            lines.append(f"| {venue} | {count} |")
    else:
        lines.append("No rejections this period.")
    lines.append("")

    return "\n".join(lines)


def post_github_issue(body):
    """Post weekly QC report as GitHub Issue."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    title = f"Weekly QC Report — {date_str}"

    # Ensure label exists
    subprocess.run(
        ["gh", "label", "create", "weekly-qc-report",
         "--description", "Automated weekly video QC report",
         "--color", "d93f0b", "--force"],
        capture_output=True
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tmp:
        tmp.write(body)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["gh", "issue", "create",
             "--title", title,
             "--body-file", tmp_path,
             "--label", "weekly-qc-report"],
            capture_output=True, text=True
        )
    finally:
        os.unlink(tmp_path)

    if result.returncode == 0:
        print(f"  Posted GitHub Issue: {result.stdout.strip()}")
    else:
        print(f"  Warning: could not create GitHub Issue: {result.stderr}")


def deliver_qc_report(report_text, days):
    """Send weekly QC report via email and append to Google Sheets."""
    end_date = datetime.now().strftime("%b %d, %Y")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%b %d")
    date_label = f"{start_date} \u2014 {end_date}"

    # --- Email ---
    body_html = markdown_to_html(report_text)
    html = wrap_html_email(body_html)
    send_email(
        subject=f"Weekly QC Report \u2014 {date_label}",
        html_body=html,
    )

    # --- Google Sheets ---
    # Parse key metrics for a summary row
    history = load_accuracy_history()
    cutoff = datetime.now() - timedelta(days=days)
    week_entries = []
    for entry in history:
        try:
            d = datetime.strptime(entry["date"], "%Y-%m-%d")
            if d >= cutoff:
                week_entries.append(entry)
        except (ValueError, KeyError):
            continue

    if week_entries:
        last = week_entries[-1]
        csv_rows = load_week_csvs(days)
        verified_count = len([r for r in csv_rows if r.get("Section") == "Verified"])
        rejected_count = len([r for r in csv_rows if r.get("Section") == "Rejected"])

        row = [
            date_label,
            last.get("accuracy_rate", ""),
            last.get("headliner_accuracy", ""),
            last.get("opener_accuracy", ""),
            last.get("avg_confidence", ""),
            last.get("verified", ""),
            last.get("rejected", ""),
            last.get("no_preview", ""),
            last.get("total_shows", ""),
            verified_count,
            rejected_count,
        ]
        append_to_sheet([row], "Weekly QC")


def main():
    parser = argparse.ArgumentParser(description="Weekly video QC report")
    parser.add_argument("--days", type=int, default=7,
                        help="Number of days to look back (default: 7)")
    parser.add_argument("--output", type=str,
                        help="Write report to file instead of posting")
    args = parser.parse_args()

    print("=" * 50)
    print("LOCAL SOUNDCHECK — WEEKLY QC REPORT")
    print("=" * 50)

    report = build_report(days=args.days)
    print(report)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\nReport written to {args.output}")
    else:
        post_github_issue(report)
        deliver_qc_report(report, args.days)


if __name__ == "__main__":
    main()
