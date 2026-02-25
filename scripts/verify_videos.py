#!/usr/bin/env python3
"""
Video Verifier — Phase 3 of the video matching pipeline.

Checks unverified YouTube video assignments against multiple signals:
- View count (reject if > 5M, unless Topic channel)
- Channel analysis (name match, type, subscriber count as modifier)
- Upload date (flag old videos with weak signals)
- Venue placeholder image (flag events masquerading as bands)

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
from datetime import datetime

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from scrapers.utils import load_env_var, normalize as _normalize

# --- Configuration ---

VIEW_COUNT_CAP = 5_000_000  # 5M views — reject if exceeded (unless Topic channel)
VIDEO_AGE_FLAG_YEARS = 15   # Flag videos older than this (not a hard reject alone)

# Known venue placeholder images — if a show uses one of these, it's likely
# an event or a band too obscure to have uploaded artwork
VENUE_PLACEHOLDERS = {
    "Cat's Cradle": "cradlevenue.png",
    "Cat's Cradle Back Room": "cradlevenue.png",
}


def load_api_key():
    """Load YouTube API key from environment or .env file."""
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


def get_video_metadata(video_id, api_key):
    """Fetch video metadata from YouTube Data API (1 quota unit)."""
    import requests
    url = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?part=snippet,statistics"
        f"&id={video_id}"
        f"&key={api_key}"
    )
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        items = resp.json().get("items", [])
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
    except Exception as e:
        print(f"  Warning: video API error for {video_id}: {e}")
        return None


def get_channel_metadata(channel_id, api_key):
    """Fetch channel metadata from YouTube Data API (1 quota unit)."""
    import requests
    url = (
        f"https://www.googleapis.com/youtube/v3/channels"
        f"?part=snippet,statistics"
        f"&id={channel_id}"
        f"&key={api_key}"
    )
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        items = resp.json().get("items", [])
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
    except Exception as e:
        print(f"  Warning: channel API error for {channel_id}: {e}")
        return None


def normalize(text):
    """Normalize text for comparison."""
    return _normalize(text)


def is_topic_channel(channel_name):
    """Check if this is a YouTube auto-generated Topic channel."""
    return channel_name.strip().endswith("- Topic")


def channel_matches_artist(channel_name, artist_name):
    """Check if the channel name relates to the artist."""
    ch = normalize(channel_name.replace("- Topic", ""))
    ar = normalize(artist_name)
    if not ch or not ar:
        return False
    return ar in ch or ch in ar


def verify_video(artist_name, video_id, venue_name, image_url, api_key):
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

    # --- Evaluate: View count ---
    views = video_meta["view_count"]
    if topic and artist_channel_match:
        # Topic channel with matching artist name — skip view count check
        metadata["view_check"] = "skipped (Topic channel match)"
    elif views > VIEW_COUNT_CAP:
        reasons.append(
            f"view count {views:,} exceeds {VIEW_COUNT_CAP:,} cap"
        )

    # --- Evaluate: Channel match ---
    if not artist_channel_match and not topic:
        # Channel doesn't match and it's not a Topic channel
        # Check subscriber count as modifier
        if channel_meta and channel_meta["subscriber_count"] > 2_000_000:
            reasons.append(
                f"non-matching channel '{video_meta['channel_name']}' "
                f"with {channel_meta['subscriber_count']:,} subscribers"
            )
        elif not artist_channel_match:
            # Weak signal — channel doesn't match but not a hard reject alone
            # unless combined with other issues
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
                reasons.append(
                    f"video is {age_years:.0f} years old with no channel match"
                )
        except (ValueError, TypeError):
            pass

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


def spotify_indicator(artist_name, spotify_cache):
    """
    Return a compact Spotify indicator for the report.
    ✓ 44 = exact match, popularity 44
    ~ 8  = close/partial match, popularity 8
    —    = not found on Spotify
    """
    entry = spotify_cache.get(artist_name, {})
    conf = entry.get("match_confidence", "")
    pop = entry.get("popularity")
    if conf == "exact":
        return f"✓ {pop}"
    elif conf in ("close", "partial"):
        return f"~ {pop}"
    elif conf == "no_match":
        return "—"
    else:
        return ""  # no cache entry at all


def build_report(tonight, states, all_shows_data, spotify_cache=None):
    """Build the daily video report text."""
    if spotify_cache is None:
        spotify_cache = {}
    date_str = datetime.now().strftime("%b %d, %Y")
    lines = []
    lines.append("LOCAL SOUNDCHECK — DAILY VIDEO REPORT")
    lines.append(date_str)
    lines.append("")

    # --- Tonight's Changes ---
    lines.append("TONIGHT'S CHANGES")
    lines.append(f"  Videos verified: {len(tonight['verified'])}")
    lines.append(f"  Videos rejected: {len(tonight['rejected'])}")
    lines.append(f"  Already verified (skipped): {tonight['already_verified']}")
    lines.append(f"  Overrides (skipped): {tonight['overrides']}")
    lines.append("")

    # --- New Verified Videos ---
    if tonight["verified"]:
        lines.append("NEW VERIFIED VIDEOS")
        lines.append(
            f"{'Artist':<20}| {'Venue':<22}| {'Date':<10}| {'Spotify':<7}"
            f"| {'Video':<48}| Confidence"
        )
        lines.append(
            f"{'-'*20}+{'-'*22}+{'-'*10}+{'-'*7}"
            f"+{'-'*48}+{'-'*20}"
        )
        for v in tonight["verified"]:
            url = f"youtube.com/watch?v={v['video_id']}"
            sp = spotify_indicator(v["artist"], spotify_cache)
            lines.append(
                f"{v['artist']:<20}| {v['venue']:<22}| {v['date']:<10}| {sp:<7}"
                f"| {url:<48}| {v['confidence']}"
            )
        lines.append("")

    # --- Rejected Candidates ---
    if tonight["rejected"]:
        lines.append("REJECTED CANDIDATES")
        lines.append(
            f"{'Artist':<20}| {'Venue':<22}| {'Date':<10}| {'Spotify':<7}"
            f"| {'Candidate':<48}| Reason"
        )
        lines.append(
            f"{'-'*20}+{'-'*22}+{'-'*10}+{'-'*7}"
            f"+{'-'*48}+{'-'*30}"
        )
        for r in tonight["rejected"]:
            url = f"youtube.com/watch?v={r['video_id']}"
            reason_str = "; ".join(r["reasons"])
            sp = spotify_indicator(r["artist"], spotify_cache)
            lines.append(
                f"{r['artist']:<20}| {r['venue']:<22}| {r['date']:<10}| {sp:<7}"
                f"| {url:<48}| {reason_str}"
            )
        lines.append("")

    # --- No Preview Queue ---
    no_preview = []
    for filepath, data in all_shows_data:
        shows = data.get("shows", data) if isinstance(data, dict) else data
        for show in shows:
            if not isinstance(show, dict):
                continue
            artist = show.get("artist", "")
            yt_id = show.get("youtube_id")
            if not yt_id and artist:
                venue = show.get("venue", "Unknown")
                date = show.get("date", "TBD")
                # Determine status — why does this show have no video?
                state = states.get(artist, {})
                state_status = state.get("status", "")
                if state_status == "rejected":
                    reason = state.get("reason", "unknown")
                    status = f"Rejected: {reason}"
                elif state_status == "override_null":
                    status = "Override: no video"
                elif state_status == "verified":
                    # Artist verified at another venue but this show
                    # doesn't have a video — scraper didn't assign one
                    status = "No video from scraper"
                else:
                    status = "No video assigned"
                no_preview.append({
                    "artist": artist,
                    "venue": venue,
                    "date": date,
                    "status": status,
                })

    if no_preview:
        lines.append(f"NO PREVIEW QUEUE ({len(no_preview)} total)")
        lines.append(
            f"{'Artist':<20}| {'Venue':<22}| {'Date':<10}| {'Spotify':<7}| Status"
        )
        lines.append(
            f"{'-'*20}+{'-'*22}+{'-'*10}+{'-'*7}+{'-'*30}"
        )
        for np in no_preview:
            sp = spotify_indicator(np["artist"], spotify_cache)
            lines.append(
                f"{np['artist']:<20}| {np['venue']:<22}| {np['date']:<10}| {sp:<7}"
                f"| {np['status']}"
            )
        lines.append("")

    lines.append(f"Generated: {datetime.now().strftime('%a %b %d, %Y %I:%M %p ET')}")
    return "\n".join(lines)


def build_csv(tonight, states, all_shows_data, spotify_cache=None):
    """Build a combined CSV with Spotify match and popularity columns."""
    if spotify_cache is None:
        spotify_cache = {}
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Section", "Artist", "Venue", "Date", "Video URL",
                     "Spotify Match", "Spotify Popularity", "Detail"])

    for v in tonight["verified"]:
        url = f"https://youtube.com/watch?v={v['video_id']}"
        entry = spotify_cache.get(v["artist"], {})
        sp_match = entry.get("match_confidence", "")
        sp_pop = entry.get("popularity", "")
        writer.writerow(["Verified", v["artist"], v["venue"], v["date"], url,
                         sp_match, sp_pop, v["confidence"]])

    for r in tonight["rejected"]:
        url = f"https://youtube.com/watch?v={r['video_id']}"
        reason_str = "; ".join(r["reasons"])
        entry = spotify_cache.get(r["artist"], {})
        sp_match = entry.get("match_confidence", "")
        sp_pop = entry.get("popularity", "")
        writer.writerow(["Rejected", r["artist"], r["venue"], r["date"], url,
                         sp_match, sp_pop, reason_str])

    # No preview queue
    for filepath, data in all_shows_data:
        shows = data.get("shows", data) if isinstance(data, dict) else data
        for show in shows:
            if not isinstance(show, dict):
                continue
            artist = show.get("artist", "")
            yt_id = show.get("youtube_id")
            if not yt_id and artist:
                venue = show.get("venue", "Unknown")
                date = show.get("date", "TBD")
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
                writer.writerow(["No Preview", artist, venue, date, "",
                                 sp_match, sp_pop, status])

    return output.getvalue()


def post_github_issue(report_text, csv_text=None):
    """Post the daily report as a GitHub Issue."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    title = f"Daily Video Report — {date_str}"
    body = f"```\n{report_text}\n```"

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

    # Create new issue
    result = subprocess.run(
        ["gh", "issue", "create",
         "--title", title,
         "--body", body,
         "--label", "daily-video-report"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        issue_url = result.stdout.strip()
        print(f"  Posted GitHub Issue: {issue_url}")

        # Attach CSV if available
        if csv_text:
            try:
                # Extract issue number from URL
                issue_number = issue_url.rstrip("/").split("/")[-1]
                csv_filename = f"video-report-{date_str}.csv"
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".csv", prefix="video-report-",
                    delete=False
                ) as tmp:
                    tmp.write(csv_text)
                    tmp_path = tmp.name
                # Upload CSV as issue comment attachment via gh
                comment_body = (
                    f"📎 CSV report attached: `{csv_filename}`\n\n"
                    "Download and open in Excel/Sheets for sorting and filtering."
                )
                subprocess.run(
                    ["gh", "issue", "comment", issue_number,
                     "--body", comment_body],
                    capture_output=True, text=True,
                )
                # Also save CSV next to the issue for the commit step to pick up
                csv_out_path = os.path.join(
                    _PROJECT_ROOT, "qa", csv_filename
                )
                with open(csv_out_path, "w") as f:
                    f.write(csv_text)
                print(f"  CSV saved to qa/{csv_filename}")
                os.unlink(tmp_path)
            except Exception as e:
                print(f"  Warning: could not attach CSV: {e}")
    else:
        print(f"  Warning: could not create GitHub Issue: {result.stderr}")


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
    all_shows_data = load_all_shows()

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
                print(f"\n  Verifying: {artist} — {video_id}")
                passed, reasons, metadata = verify_video(
                    artist, video_id, venue, image, api_key
                )
                api_calls += 2  # video + channel metadata

                if passed:
                    confidence = []
                    if metadata.get("channel_match"):
                        confidence.append("channel match")
                    if metadata.get("is_topic"):
                        confidence.append("Topic channel")
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

    # Load Spotify cache for report annotations
    spotify_cache = load_spotify_cache()

    # Build report and CSV
    report = build_report(tonight, states, all_shows_data, spotify_cache)
    csv_text = build_csv(tonight, states, all_shows_data, spotify_cache)

    print("\n" + "=" * 50)
    print(report)
    print("=" * 50)

    print(f"\nAPI calls: ~{api_calls} units")
    print(f"Verified: {len(tonight['verified'])} | "
          f"Rejected: {len(tonight['rejected'])} | "
          f"Skipped: {tonight['already_verified']} already verified, "
          f"{tonight['overrides']} overrides")

    # Output
    if args.output:
        with open(args.output, "w") as f:
            f.write(report + "\n")
        # Also write CSV alongside the text report
        csv_path = args.output.rsplit(".", 1)[0] + ".csv"
        with open(csv_path, "w") as f:
            f.write(csv_text)
        print(f"\nReport written to {args.output}")
        print(f"CSV written to {csv_path}")
    elif not args.dry_run:
        post_github_issue(report, csv_text=csv_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
