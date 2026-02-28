#!/usr/bin/env python3
"""
Video Verifier — Phase 3 of the video matching pipeline.

Checks unverified YouTube video assignments against multiple signals:
- View count (tiered caps: 5M default, 10-50M with Spotify popularity, 50M for trusted labels/VEVO)
- Trusted channel detection (label allowlist + VEVO — bypasses mismatch/age/Spotify rejections)
- Channel analysis (name match, type, subscriber count as modifier)
- Upload date (flag old videos with weak signals)
- Venue placeholder image (flag events masquerading as bands)
- Spotify identity (reject if not found on Spotify AND channel doesn't match AND not trusted)

Runs after scrapers in the nightly GitHub Actions workflow.
Reads all data/shows-*.json files and qa/video_states.json.
Updates show files (nulls out rejected videos) and generates daily report.

Usage:
    python scripts/verify_videos.py                  # Normal run + GitHub Issue
    python scripts/verify_videos.py --output report.txt   # Output to file instead
    python scripts/verify_videos.py --dry-run        # Check without modifying files
"""

import csv
import io
import os
import sys
import json
import re
import subprocess
import tempfile
import time
from datetime import datetime

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from scrapers.utils import load_env_var, normalize as _normalize
from scripts.report_delivery import (
    send_email, append_to_sheet, markdown_to_html, wrap_html_email,
)

# --- Configuration ---

VIEW_COUNT_CAP = 5_000_000  # 5M views — reject if exceeded (unless Topic channel)
VIDEO_AGE_FLAG_YEARS = 15   # Flag videos older than this (not a hard reject alone)

# Known venue placeholder images — if a show uses one of these, it's likely
# an event or a band too obscure to have uploaded artwork
VENUE_PLACEHOLDERS = {
    "Cat's Cradle": "cradlevenue.png",
    "Cat's Cradle Back Room": "cradlevenue.png",
}

# Trusted record labels — videos on these channels should not be rejected
# for channel mismatch or high subscriber counts. View cap raised to 50M.
# Keys are pre-normalized (lowercase, non-alphanumeric stripped).
TRUSTED_LABELS = {
    "nuclearblastrecords": "Nuclear Blast Records",
    "epitaphrecords": "Epitaph Records",
    "fueledbyramen": "Fueled By Ramen",
    "spinninrecords": "Spinnin' Records",
    "secretcityrecords": "Secret City Records",
    "innovativeleisure": "Innovative Leisure",
    "sideonedummy": "SideOneDummy",
    "riserecords": "Rise Records",
    "fearlessrecords": "Fearless Records",
    "centurymediarecords": "Century Media Records",
    "newwestrecords": "New West Records",
    "flightlessrecords": "Flightless Records",
    "warnerrecords": "Warner Records",
    "carparkrecords": "Carpark Records",
}

TRUSTED_CHANNEL_VIEW_CAP = 50_000_000  # 50M — raised cap for trusted labels/VEVO

# Spotify-popularity-aware view count caps.
# Higher popularity = higher acceptable view count.
# Ordered highest to lowest; first matching tier wins.
SPOTIFY_VIEW_CAPS = [
    (70, None),          # popularity >= 70: no cap (major artist)
    (50, 50_000_000),    # popularity >= 50: 50M cap
    (30, 10_000_000),    # popularity >= 30: 10M cap
]
DEFAULT_VIEW_CAP = VIEW_COUNT_CAP  # 5M when no Spotify data or popularity < 30


def load_api_key():
    """Load YouTube API key from environment or .env file.

    Prefers YOUTUBE_VERIFIER_API_KEY (dedicated verifier quota) and
    falls back to YOUTUBE_API_KEY (shared with scrapers).
    """
    key = load_env_var("YOUTUBE_VERIFIER_API_KEY")
    if key:
        return key
    return load_env_var("YOUTUBE_API_KEY")


def load_overrides():
    """Load overrides.json."""
    path = os.path.join(_PROJECT_ROOT, "scrapers", "overrides.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def load_video_states():
    """Load verification state for all artists."""
    path = os.path.join(_PROJECT_ROOT, "qa", "video_states.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_video_states(states):
    """Save verification state."""
    path = os.path.join(_PROJECT_ROOT, "qa", "video_states.json")
    with open(path, "w") as f:
        json.dump(states, f, indent=2)
        f.write("\n")


def load_all_shows():
    """Load all show data files. Returns list of (filepath, data) tuples."""
    data_dir = os.path.join(_PROJECT_ROOT, "data")
    results = []
    for filename in sorted(os.listdir(data_dir)):
        if filename.startswith("shows-") and filename.endswith(".json"):
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath) as f:
                    data = json.load(f)
                results.append((filepath, data))
            except (json.JSONDecodeError, FileNotFoundError):
                print(f"  Warning: could not read {filename}")
    return results


def _youtube_api_get(url, resource_label, max_retries=2):
    """Make a YouTube Data API GET request with retry on transient errors.

    Retries up to max_retries times on 429/503 with 2s backoff.
    Returns parsed JSON items list, or None on failure.
    """
    import requests
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("items", [])
            if resp.status_code in (429, 503) and attempt < max_retries:
                print(f"  Retry {attempt + 1}/{max_retries}: YouTube API returned {resp.status_code} for {resource_label}")
                time.sleep(2)
                continue
            print(f"  Warning: YouTube API returned {resp.status_code} for {resource_label}")
            return None
        except Exception as e:
            print(f"  Warning: YouTube API error for {resource_label}: {e}")
            return None


def get_video_metadata(video_id, api_key):
    """Fetch video metadata from YouTube Data API (1 quota unit)."""
    url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet,statistics"
        f"&id={video_id}"
        f"&key={api_key}"
    )
    items = _youtube_api_get(url, f"video {video_id}")
    if not items:
        return None
    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    return {
        "title": snippet.get("title", ""),
        "channel_name": snippet.get("channelTitle", ""),
        "channel_id": snippet.get("channelId", ""),
        "published": snippet.get("publishedAt", ""),
        "view_count": int(stats.get("viewCount", 0)),
    }


def get_channel_metadata(channel_id, api_key):
    """Fetch channel metadata from YouTube Data API (1 quota unit)."""
    url = (
        f"https://www.googleapis.com/youtube/v3/channels"
        f"?part=snippet,statistics"
        f"&id={channel_id}"
        f"&key={api_key}"
    )
    items = _youtube_api_get(url, f"channel {channel_id}")
    if not items:
        return None
    item = items[0]
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    return {
        "name": snippet.get("title", ""),
        "subscriber_count": int(stats.get("subscriberCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
    }


def is_topic_channel(channel_name):
    """Check if this is a YouTube auto-generated Topic channel."""
    return channel_name.strip().endswith("- Topic")


def channel_matches_artist(channel_name, artist_name):
    """Check if the channel name relates to the artist."""
    ch = _normalize(channel_name.replace("- Topic", ""))
    ar = _normalize(artist_name)
    if not ch or not ar:
        return False
    return ar in ch or ch in ar


def verify_video(artist_name, video_id, venue_name, image_url, api_key,
                  spotify_entry=None):
    """
    Run all verification checks on a single video.
    Returns (passed: bool, reasons: list[str], metadata: dict).
    """
    reasons = []
    metadata = {}

    # --- Check 1: Venue placeholder image ---
    placeholder = VENUE_PLACEHOLDERS.get(venue_name, "")
    if placeholder and image_url and placeholder in image_url:
        reasons.append(f"venue placeholder image ({placeholder})")

    # --- Check 2: Video metadata ---
    video_meta = get_video_metadata(video_id, api_key)
    if not video_meta:
        reasons.append("could not fetch video metadata")
        return False, reasons, metadata

    metadata["video_title"] = video_meta["title"]
    metadata["channel_name"] = video_meta["channel_name"]
    metadata["view_count"] = video_meta["view_count"]
    metadata["published"] = video_meta["published"]

    # --- Check 3: Channel metadata ---
    channel_meta = get_channel_metadata(video_meta["channel_id"], api_key)
    if channel_meta:
        metadata["channel_subscribers"] = channel_meta["subscriber_count"]
        metadata["channel_videos"] = channel_meta["video_count"]

    # --- Evaluate: Topic channel? ---
    topic = is_topic_channel(video_meta["channel_name"])
    metadata["is_topic"] = topic
    artist_channel_match = channel_matches_artist(
        video_meta["channel_name"], artist_name
    )
    metadata["channel_match"] = artist_channel_match

    # --- Evaluate: Trusted channel (label allowlist / VEVO) ---
    trusted_channel = False
    trusted_reason = ""
    norm_channel = _normalize(video_meta["channel_name"])
    if norm_channel in TRUSTED_LABELS:
        trusted_channel = True
        trusted_reason = f"label: {TRUSTED_LABELS[norm_channel]}"
        metadata["trusted_label"] = TRUSTED_LABELS[norm_channel]
    elif norm_channel.endswith("vevo"):
        trusted_channel = True
        trusted_reason = "VEVO"
        metadata["vevo_channel"] = True
    metadata["trusted_channel"] = trusted_channel
    if trusted_reason:
        metadata["trusted_reason"] = trusted_reason

    # --- Evaluate: View count ---
    views = video_meta["view_count"]
    if topic and artist_channel_match:
        # Topic channel with matching artist name — skip view count check
        metadata["view_check"] = "skipped (Topic channel match)"
    else:
        # Determine effective view cap based on trust signals
        if trusted_channel:
            effective_cap = TRUSTED_CHANNEL_VIEW_CAP
            metadata["view_cap_reason"] = f"trusted channel ({trusted_reason})"
        elif spotify_entry and spotify_entry.get("popularity") is not None:
            sp_pop = spotify_entry.get("popularity", 0)
            effective_cap = DEFAULT_VIEW_CAP
            cap_reason = f"Spotify popularity {sp_pop}"
            for min_pop, cap in SPOTIFY_VIEW_CAPS:
                if sp_pop >= min_pop:
                    effective_cap = cap
                    cap_reason = f"Spotify popularity {sp_pop} (>={min_pop})"
                    break
            metadata["view_cap_reason"] = cap_reason
        else:
            effective_cap = DEFAULT_VIEW_CAP
            metadata["view_cap_reason"] = "default (no trust signals)"

        if effective_cap is not None and views > effective_cap:
            reasons.append(
                f"view count {views:,} exceeds {effective_cap:,} cap"
            )

    # --- Evaluate: Channel match ---
    if not artist_channel_match and not topic:
        if trusted_channel:
            # Trusted label/VEVO — don't penalize for channel mismatch
            metadata["channel_override"] = (
                f"trusted {trusted_reason}, skipping mismatch check"
            )
        elif channel_meta and channel_meta["subscriber_count"] > 2_000_000:
            reasons.append(
                f"non-matching channel '{video_meta['channel_name']}' "
                f"with {channel_meta['subscriber_count']:,} subscribers"
            )
        else:
            # Weak signal — channel doesn't match but not a hard reject alone
            metadata["channel_warning"] = (
                f"channel '{video_meta['channel_name']}' doesn't match artist"
            )

    # --- Evaluate: Upload date ---
    if video_meta["published"]:
        try:
            pub_date = datetime.fromisoformat(
                video_meta["published"].replace("Z", "+00:00")
            )
            age_years = (datetime.now(pub_date.tzinfo) - pub_date).days / 365.25
            metadata["video_age_years"] = round(age_years, 1)
            if age_years > VIDEO_AGE_FLAG_YEARS and not artist_channel_match:
                if trusted_channel:
                    metadata["age_override"] = (
                        f"trusted {trusted_reason}, skipping age check"
                    )
                else:
                    reasons.append(
                        f"video is {age_years:.0f} years old with no channel match"
                    )
        except (ValueError, TypeError):
            pass

    # --- Evaluate: Spotify identity check ---
    # If Spotify can't confirm this is a real artist AND the channel doesn't
    # match, that's a strong signal the video is wrong
    if spotify_entry:
        sp_conf = spotify_entry.get("match_confidence", "")
        sp_pop = spotify_entry.get("popularity")
        metadata["spotify_match"] = sp_conf
        metadata["spotify_popularity"] = sp_pop

        if sp_conf == "no_match" and not artist_channel_match and not topic:
            if trusted_channel:
                metadata["spotify_override"] = (
                    f"trusted {trusted_reason}, skipping Spotify no_match rejection"
                )
            else:
                reasons.append("not found on Spotify + channel mismatch")
        elif (sp_conf in ("close", "partial")
              and not artist_channel_match and not topic):
            sp_name = spotify_entry.get("spotify_name", "?")
            metadata["spotify_warning"] = (
                f"Spotify matched '{sp_name}' (not exact)"
                f" and channel doesn't match"
            )

    passed = len(reasons) == 0
    return passed, reasons, metadata


def load_spotify_cache():
    """Load Spotify enrichment cache for report annotations."""
    path = os.path.join(_PROJECT_ROOT, "qa", "spotify_cache.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def spotify_csv_indicator(artist_name, spotify_cache):
    """Return Spotify match/popularity as 'match (pop)' for CSV-friendly format."""
    entry = spotify_cache.get(artist_name, {})
    conf = entry.get("match_confidence", "")
    pop = entry.get("popularity", "")
    if conf:
        return f"{conf} ({pop})" if pop != "" else conf
    return ""


def load_latest_audit():
    """Load the most recent audit file and return overall stats."""
    import glob as _glob
    audit_dir = os.path.join(_PROJECT_ROOT, "qa", "audits")
    files = sorted(_glob.glob(os.path.join(audit_dir, "*.json")))
    if not files:
        return None
    try:
        with open(files[-1]) as f:
            data = json.load(f)
        return data.get("overall", {})
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def load_accuracy_history():
    """Load accuracy history from qa/accuracy_history.json."""
    path = os.path.join(_PROJECT_ROOT, "qa", "accuracy_history.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_accuracy_history(history):
    """Save accuracy history."""
    path = os.path.join(_PROJECT_ROOT, "qa", "accuracy_history.json")
    with open(path, "w") as f:
        json.dump(history, f, indent=2)
        f.write("\n")


def compute_inventory(states, all_shows_data):
    """Count verified/rejected/no-preview per venue across all shows.

    Counts both headliners and openers, with per-role breakdowns.

    Returns (totals_dict, venue_dict) where:
      totals = {"verified": N, "rejected": N, "no_preview": N, "override": N, "total": N,
                "headliner_verified": N, "headliner_total": N,
                "opener_verified": N, "opener_total": N}
      venues = {"Venue Name": {"with_video": N, "total": N}, ...}
    """
    totals = {"verified": 0, "rejected": 0, "no_preview": 0, "override": 0, "total": 0,
              "headliner_verified": 0, "headliner_total": 0,
              "opener_verified": 0, "opener_total": 0}
    venues = {}

    for filepath, data in all_shows_data:
        shows = data.get("shows", data) if isinstance(data, dict) else data
        for show in shows:
            if not isinstance(show, dict):
                continue

            venue = show.get("venue", "Unknown")
            if venue not in venues:
                venues[venue] = {"with_video": 0, "total": 0}

            for role, name_key, id_key in [
                ("headliner", "artist", "youtube_id"),
                ("opener", "opener", "opener_youtube_id"),
            ]:
                artist = show.get(name_key, "")
                if not artist:
                    continue
                yt_id = show.get(id_key)

                venues[venue]["total"] += 1
                totals["total"] += 1
                totals[f"{role}_total"] += 1

                if yt_id:
                    venues[venue]["with_video"] += 1
                    totals["verified"] += 1
                    totals[f"{role}_verified"] += 1
                else:
                    state = states.get(artist, {})
                    status = state.get("status", "")
                    if status == "rejected":
                        totals["rejected"] += 1
                    elif status == "override_null":
                        totals["override"] += 1
                    else:
                        totals["no_preview"] += 1

    return totals, venues


def build_issue_body(tonight, states, all_shows_data, old_states,
                     spotify_cache=None):
    """Build the daily video report as a GitHub-flavored markdown issue body.

    Sections:
      1. Tonight's Delta — newly verified, rejected, and recovered
      2. Full Inventory — coverage stats by venue
      3. Accuracy — from latest audit + history
    """
    if spotify_cache is None:
        spotify_cache = {}
    date_str = datetime.now().strftime("%b %d, %Y")
    csv_filename = f"video-report-{datetime.now().strftime('%Y-%m-%d')}.csv"

    # --- Detect recoveries: was rejected before, now verified ---
    recovered = []
    for v in tonight["verified"]:
        prev = old_states.get(v["artist"])
        if prev == "rejected":
            # Look up old reason from states snapshot
            recovered.append(v)

    lines = [f"# Daily Video Report — {date_str}", ""]

    # --- Section 1: Tonight's Delta ---
    n_verified = len(tonight["verified"])
    n_rejected = len(tonight["rejected"])
    n_recovered = len(recovered)
    lines.append("## Tonight's Delta")
    lines.append(
        f"**{n_verified} verified | {n_rejected} rejected | "
        f"{n_recovered} recovered | "
        f"{tonight['already_verified']} unchanged | "
        f"{tonight['overrides']} overrides**"
    )
    lines.append("")

    if tonight["verified"]:
        lines.append("### Newly Verified")
        lines.append("| Artist | Venue | Date | Spotify | Detail |")
        lines.append("|--------|-------|------|---------|--------|")
        for v in tonight["verified"]:
            sp = spotify_csv_indicator(v["artist"], spotify_cache)
            lines.append(
                f"| {v['artist']} | {v['venue']} | {v['date']} "
                f"| {sp} | {v['confidence']} |"
            )
        lines.append("")

    if tonight["rejected"]:
        lines.append("### Newly Rejected")
        lines.append("| Artist | Venue | Date | Spotify | Reason |")
        lines.append("|--------|-------|------|---------|--------|")
        for r in tonight["rejected"]:
            reason_str = "; ".join(r["reasons"])
            sp = spotify_csv_indicator(r["artist"], spotify_cache)
            lines.append(
                f"| {r['artist']} | {r['venue']} | {r['date']} "
                f"| {sp} | {reason_str} |"
            )
        lines.append("")

    if recovered:
        lines.append("### Recovered (previously failed, now verified)")
        lines.append("| Artist | Venue | Detail |")
        lines.append("|--------|-------|--------|")
        for v in recovered:
            lines.append(
                f"| {v['artist']} | {v['venue']} | {v['confidence']} |"
            )
        lines.append("")

    # --- Section 2: Full Inventory ---
    totals, venues = compute_inventory(states, all_shows_data)
    lines.append("## Full Inventory")
    lines.append("| Status | Count | % |")
    lines.append("|--------|------:|----:|")
    total = totals["total"] or 1  # avoid division by zero
    for status_key, label in [("verified", "Verified"),
                               ("rejected", "Rejected"),
                               ("no_preview", "No Preview"),
                               ("override", "Override")]:
        count = totals[status_key]
        pct = round(count / total * 100)
        lines.append(f"| {label} | {count} | {pct}% |")
    lines.append(f"| **Total** | **{totals['total']}** | |")
    lines.append("")

    # Per-venue breakdown table
    lines.append("| Venue | With Video | Total | % |")
    lines.append("|-------|----------:|------:|----:|")
    for vname in sorted(venues.keys()):
        v = venues[vname]
        vpct = round(v["with_video"] / v["total"] * 100) if v["total"] else 0
        lines.append(f"| {vname} | {v['with_video']} | {v['total']} | {vpct}% |")
    lines.append("")
    lines.append(f"Full detail: `qa/{csv_filename}`")
    lines.append("")

    # --- Section 3: Accuracy ---
    audit = load_latest_audit()
    history = load_accuracy_history()
    lines.append("## Accuracy")
    if audit:
        today_acc = audit.get("accuracy_rate", 0)
        today_conf = audit.get("avg_confidence", 0)

        # Yesterday and 7-day average from history
        yesterday_acc = ""
        yesterday_conf = ""
        avg_7_acc = ""
        avg_7_conf = ""
        if history:
            yesterday_acc = history[-1].get("accuracy_rate", "")
            yesterday_conf = history[-1].get("avg_confidence", "")
            recent = history[-7:]
            acc_vals = [h["accuracy_rate"] for h in recent
                        if "accuracy_rate" in h]
            conf_vals = [h["avg_confidence"] for h in recent
                         if "avg_confidence" in h]
            if acc_vals:
                avg_7_acc = f"{sum(acc_vals)/len(acc_vals):.1f}%"
            if conf_vals:
                avg_7_conf = f"{sum(conf_vals)/len(conf_vals):.1f}"
            yesterday_acc = f"{yesterday_acc}%" if yesterday_acc else "—"
            yesterday_conf = str(yesterday_conf) if yesterday_conf else "—"

        overrides = load_overrides()
        override_count = len(overrides.get("artist_youtube", {}))

        lines.append("| Metric | Today | Yesterday | 7-day avg |")
        lines.append("|--------|------:|----------:|----------:|")
        lines.append(
            f"| Accuracy | {today_acc}% | {yesterday_acc or '—'} "
            f"| {avg_7_acc or '—'} |"
        )
        lines.append(
            f"| Avg confidence | {today_conf} | {yesterday_conf or '—'} "
            f"| {avg_7_conf or '—'} |"
        )
        lines.append(f"| Overrides | {override_count} | | |")
        # Role accuracy breakdown
        hl_total = totals.get("headliner_total", 0)
        hl_verified = totals.get("headliner_verified", 0)
        op_total = totals.get("opener_total", 0)
        op_verified = totals.get("opener_verified", 0)
        hl_pct = f"{round(hl_verified / hl_total * 100, 1)}%" if hl_total else "—"
        op_pct = f"{round(op_verified / op_total * 100, 1)}%" if op_total else "—"
        lines.append(
            f"| **Headliner** | **{hl_pct}** ({hl_verified}/{hl_total}) | | |"
        )
        lines.append(
            f"| **Opener** | **{op_pct}** ({op_verified}/{op_total}) | | |"
        )
    else:
        lines.append("No audit data available yet.")
    lines.append("")

    return "\n".join(lines)


def build_csv(tonight, states, all_shows_data, old_states,
              spotify_cache=None):
    """Build a combined CSV with Spotify match, popularity, and Changed columns."""
    if spotify_cache is None:
        spotify_cache = {}

    # Build set of recovered artists (rejected before, verified now)
    recovered_artists = set()
    for v in tonight["verified"]:
        if old_states.get(v["artist"]) == "rejected":
            recovered_artists.add(v["artist"])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Section", "Artist", "Role", "Venue", "Date", "Video URL",
                     "Spotify Match", "Spotify Popularity", "Detail",
                     "Changed"])

    for v in tonight["verified"]:
        url = f"https://youtube.com/watch?v={v['video_id']}"
        entry = spotify_cache.get(v["artist"], {})
        sp_match = entry.get("match_confidence", "")
        sp_pop = entry.get("popularity", "")
        changed = "Recovered" if v["artist"] in recovered_artists else "New"
        writer.writerow(["Verified", v["artist"], v.get("role", "headliner"),
                         v["venue"], v["date"], url,
                         sp_match, sp_pop, v["confidence"], changed])

    for r in tonight["rejected"]:
        url = f"https://youtube.com/watch?v={r['video_id']}"
        reason_str = "; ".join(r["reasons"])
        entry = spotify_cache.get(r["artist"], {})
        sp_match = entry.get("match_confidence", "")
        sp_pop = entry.get("popularity", "")
        writer.writerow(["Rejected", r["artist"], r.get("role", "headliner"),
                         r["venue"], r["date"], url,
                         sp_match, sp_pop, reason_str, "New"])

    # No preview queue — check both headliners and openers
    for filepath, data in all_shows_data:
        shows = data.get("shows", data) if isinstance(data, dict) else data
        for show in shows:
            if not isinstance(show, dict):
                continue
            venue = show.get("venue", "Unknown")
            date = show.get("date", "TBD")

            for role, name_key, id_key in [
                ("headliner", "artist", "youtube_id"),
                ("opener", "opener", "opener_youtube_id"),
            ]:
                artist = show.get(name_key, "")
                yt_id = show.get(id_key)
                if not artist or yt_id:
                    continue
                state = states.get(artist, {})
                state_status = state.get("status", "")
                if state_status == "rejected":
                    status = f"Rejected: {state.get('reason', 'unknown')}"
                elif state_status == "override_null":
                    status = "Override: no video"
                elif state_status == "verified":
                    status = "No video from scraper"
                else:
                    status = "No video assigned"
                entry = spotify_cache.get(artist, {})
                sp_match = entry.get("match_confidence", "")
                sp_pop = entry.get("popularity", "")
                writer.writerow(["No Preview", artist, role, venue, date, "",
                                 sp_match, sp_pop, status, ""])

    return output.getvalue()


def post_github_issue(issue_body, csv_text=None):
    """Post the daily report as a GitHub Issue with markdown body.

    The issue body is markdown (not wrapped in a code block).
    CSV is saved to qa/ for the commit step — no longer posted as a comment.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    title = f"Daily Video Report — {date_str}"

    # Ensure label exists
    subprocess.run(
        ["gh", "label", "create", "daily-video-report",
         "--description", "Automated daily video verification report",
         "--color", "1d76db", "--force"],
        capture_output=True
    )

    # Close previous daily report issues
    result = subprocess.run(
        ["gh", "issue", "list", "--label", "daily-video-report",
         "--state", "open", "--json", "number", "--limit", "10"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        try:
            issues = json.loads(result.stdout)
            for issue in issues:
                subprocess.run(
                    ["gh", "issue", "close", str(issue["number"])],
                    capture_output=True
                )
        except json.JSONDecodeError:
            pass

    # Create new issue — use tempfile to avoid shell escaping issues
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md",
                                     delete=False) as tmp:
        tmp.write(issue_body)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["gh", "issue", "create",
             "--title", title,
             "--body-file", tmp_path,
             "--label", "daily-video-report"],
            capture_output=True, text=True
        )
    finally:
        os.unlink(tmp_path)

    if result.returncode == 0:
        issue_url = result.stdout.strip()
        print(f"  Posted GitHub Issue: {issue_url}")
    else:
        print(f"  Warning: could not create GitHub Issue: {result.stderr}")

    # Save CSV to qa/ for the commit step to pick up
    if csv_text:
        csv_filename = f"video-report-{date_str}.csv"
        csv_out_path = os.path.join(_PROJECT_ROOT, "qa", csv_filename)
        with open(csv_out_path, "w") as f:
            f.write(csv_text)
        print(f"  CSV saved to qa/{csv_filename}")


def deliver_daily_report(issue_body, csv_text):
    """Send daily video report via email and append to Google Sheets."""
    date_str = datetime.now().strftime("%b %d, %Y")

    # --- Email ---
    body_html = markdown_to_html(issue_body)
    sheet_id = load_env_var("REPORT_SHEETS_ID")
    footer = "View full detail in Google Sheets" if sheet_id else None
    html = wrap_html_email(body_html, footer_text=footer)

    attachments = None
    if csv_text:
        csv_filename = f"video-report-{datetime.now().strftime('%Y-%m-%d')}.csv"
        attachments = [(csv_filename, csv_text)]

    send_email(
        subject=f"Daily Video Report \u2014 {date_str}",
        html_body=html,
        attachments=attachments,
    )

    # --- Google Sheets ---
    if csv_text:
        report_date = datetime.now().strftime("%Y-%m-%d")
        reader = csv.reader(io.StringIO(csv_text))
        header = next(reader, None)
        rows = []
        for row in reader:
            rows.append([report_date] + row)
        if rows:
            # Prepend "Report Date" to the header concept — but we only
            # append data rows (header written once when sheet is created)
            append_to_sheet(rows, "Daily Video Reports")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Verify YouTube video assignments")
    parser.add_argument("--output", help="Write report to file instead of GitHub Issue")
    parser.add_argument("--dry-run", action="store_true",
                        help="Check without modifying files")
    args = parser.parse_args()

    print("=" * 50)
    print("LOCAL SOUNDCHECK — VIDEO VERIFIER")
    print("=" * 50)

    api_key = load_api_key()
    if not api_key:
        print("Error: No YouTube API key found")
        sys.exit(1)

    overrides = load_overrides()
    artist_overrides = overrides.get("artist_youtube", {})
    opener_overrides = overrides.get("opener_youtube", {})
    states = load_video_states()
    spotify_cache = load_spotify_cache()
    all_shows_data = load_all_shows()

    # Snapshot old states before verification (for recovery detection)
    old_states = {k: v.get("status") for k, v in states.items()}

    tonight = {
        "verified": [],
        "rejected": [],
        "already_verified": 0,
        "overrides": 0,
    }

    api_calls = 0

    for filepath, data in all_shows_data:
        shows = data.get("shows", data) if isinstance(data, dict) else data
        modified = False

        for show in shows:
            if not isinstance(show, dict):
                continue

            # Process headliner and opener
            for role, name_key, id_key, override_dict in [
                ("headliner", "artist", "youtube_id", artist_overrides),
                ("opener", "opener", "opener_youtube_id", opener_overrides),
            ]:
                artist = show.get(name_key, "")
                video_id = show.get(id_key)
                if not artist or not video_id:
                    continue

                venue = show.get("venue", "Unknown")
                date = show.get("date", "TBD")
                image = show.get("image", "")

                # Skip if overridden (locked)
                if artist in override_dict:
                    tonight["overrides"] += 1
                    continue

                # Skip if already verified
                state = states.get(artist, {})
                if (state.get("status") == "verified"
                        and state.get("video_id") == video_id):
                    tonight["already_verified"] += 1
                    continue

                # --- Verify this video ---
                time.sleep(1.0)  # Throttle API requests to avoid per-second rate limits
                print(f"\n  Verifying: {artist} — {video_id}")
                sp_entry = spotify_cache.get(artist)
                passed, reasons, metadata = verify_video(
                    artist, video_id, venue, image, api_key,
                    spotify_entry=sp_entry
                )
                api_calls += 2  # video + channel metadata

                if passed:
                    confidence = []
                    if metadata.get("channel_match"):
                        confidence.append("channel match")
                    if metadata.get("is_topic"):
                        confidence.append("Topic channel")
                    if metadata.get("trusted_label"):
                        confidence.append(f"label: {metadata['trusted_label']}")
                    elif metadata.get("vevo_channel"):
                        confidence.append("VEVO")
                    views = metadata.get("view_count", 0)
                    if views < 1_000_000:
                        confidence.append(f"{views:,} views")
                    conf_str = ", ".join(confidence) if confidence else "passed all checks"

                    states[artist] = {
                        "status": "verified",
                        "video_id": video_id,
                        "verified_date": datetime.now().isoformat(),
                        "confidence": conf_str,
                        "metadata": metadata,
                    }
                    tonight["verified"].append({
                        "artist": artist,
                        "venue": venue,
                        "date": date,
                        "video_id": video_id,
                        "confidence": conf_str,
                        "role": role,
                    })
                    print(f"    ✓ Verified ({conf_str})")
                else:
                    reason_str = "; ".join(reasons)
                    states[artist] = {
                        "status": "rejected",
                        "video_id": video_id,
                        "rejected_date": datetime.now().isoformat(),
                        "reason": reason_str,
                        "metadata": metadata,
                    }
                    tonight["rejected"].append({
                        "artist": artist,
                        "venue": venue,
                        "date": date,
                        "video_id": video_id,
                        "reasons": reasons,
                        "role": role,
                    })
                    # Null out the rejected video in show data
                    if not args.dry_run:
                        show[id_key] = None
                        modified = True
                    print(f"    ✗ Rejected: {reason_str}")

        # Save modified show data
        if modified and not args.dry_run:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
            print(f"  Updated: {os.path.basename(filepath)}")

    # Save verification states
    if not args.dry_run:
        save_video_states(states)
        print(f"\nSaved {len(states)} video states to qa/video_states.json")

    # Mark null overrides in states (for report)
    for artist, vid in artist_overrides.items():
        if vid is None and artist not in states:
            states[artist] = {"status": "override_null"}
    for artist, vid in opener_overrides.items():
        if vid is None and artist not in states:
            states[artist] = {"status": "override_null"}

    # Build issue body and CSV (spotify_cache already loaded above)
    issue_body = build_issue_body(tonight, states, all_shows_data,
                                  old_states, spotify_cache)
    csv_text = build_csv(tonight, states, all_shows_data,
                         old_states, spotify_cache)

    print("\n" + "=" * 50)
    print(issue_body)
    print("=" * 50)

    print(f"\nAPI calls: ~{api_calls} units")
    print(f"Verified: {len(tonight['verified'])} | "
          f"Rejected: {len(tonight['rejected'])} | "
          f"Skipped: {tonight['already_verified']} already verified, "
          f"{tonight['overrides']} overrides")

    # Append accuracy history
    if not args.dry_run:
        audit = load_latest_audit()
        totals, _ = compute_inventory(states, all_shows_data)
        history = load_accuracy_history()
        # Compute per-role accuracy from inventory counts
        hl_total = totals["headliner_total"]
        hl_verified = totals["headliner_verified"]
        op_total = totals["opener_total"]
        op_verified = totals["opener_verified"]
        hl_accuracy = round(hl_verified / hl_total * 100, 1) if hl_total > 0 else 0
        op_accuracy = round(op_verified / op_total * 100, 1) if op_total > 0 else 0

        entry = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_shows": totals["total"],
            "verified": totals["verified"],
            "rejected": totals["rejected"],
            "no_preview": totals["no_preview"],
            "overrides": totals["override"],
            "headliner_verified": hl_verified,
            "headliner_total": hl_total,
            "headliner_accuracy": hl_accuracy,
            "opener_verified": op_verified,
            "opener_total": op_total,
            "opener_accuracy": op_accuracy,
        }
        if audit:
            entry["accuracy_rate"] = audit.get("accuracy_rate", 0)
            entry["avg_confidence"] = audit.get("avg_confidence", 0)
        history.append(entry)
        save_accuracy_history(history)
        print(f"  Appended accuracy history for {entry['date']}")

    # Output
    if args.output:
        with open(args.output, "w") as f:
            f.write(issue_body + "\n")
        # Also write CSV alongside the report
        csv_path = args.output.rsplit(".", 1)[0] + ".csv"
        with open(csv_path, "w") as f:
            f.write(csv_text)
        print(f"\nReport written to {args.output}")
        print(f"CSV written to {csv_path}")
    elif not args.dry_run:
        post_github_issue(issue_body, csv_text=csv_text)
        deliver_daily_report(issue_body, csv_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
