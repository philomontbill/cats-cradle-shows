#!/usr/bin/env python3
"""
YouTube Match Accuracy Audit

Checks every youtube_id in show data against the actual YouTube video
title and channel name. Scores confidence for each match and saves
timestamped results to qa/audits/.

Uses YouTube's oEmbed endpoint (no API key required).

Usage:
    python qa/audit_accuracy.py                # Audit all venues
    python qa/audit_accuracy.py --venue catscradle  # Audit one venue
    python qa/audit_accuracy.py --dry-run      # Show what would be audited
"""

import json
import glob
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

DATA_DIR = "data"
AUDIT_DIR = "qa/audits"

# --- String matching utilities ---

def normalize(name):
    """Normalize a name for comparison: lowercase, strip punctuation, remove common prefixes."""
    if not name:
        return ""
    name = name.lower().strip()
    # Remove common prefixes/suffixes
    name = re.sub(r"^the\s+", "", name)
    # Remove tour names and parenthetical info
    name = re.sub(r"\s*[-–—]\s*(tour|us tour|headline tour|album release).*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*\(.*?\)", "", name)
    # Remove punctuation
    name = re.sub(r"[^\w\s]", "", name)
    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


def word_set(text):
    """Get set of meaningful words (3+ chars) from text."""
    return set(w for w in normalize(text).split() if len(w) >= 3)


def score_match(artist_name, video_title, channel_name):
    """
    Score how well a YouTube video matches an artist name.
    Returns (score 0-100, explanation string).
    """
    if not artist_name or (not video_title and not channel_name):
        return 0, "no data to compare"

    artist_norm = normalize(artist_name)
    title_norm = normalize(video_title or "")
    channel_norm = normalize(channel_name or "")

    # Exact match in channel name (strongest signal)
    if artist_norm and artist_norm in channel_norm:
        return 95, f"artist name found in channel name"

    if artist_norm and artist_norm in title_norm:
        return 90, f"artist name found in video title"

    # Check channel contains artist
    if channel_norm and channel_norm in artist_norm:
        return 85, f"channel name found in artist name"

    # Word overlap scoring
    artist_words = word_set(artist_name)
    title_words = word_set(video_title or "")
    channel_words = word_set(channel_name or "")

    if not artist_words:
        return 0, "no meaningful words in artist name"

    # Check overlap with channel
    channel_overlap = artist_words & channel_words
    if channel_overlap:
        ratio = len(channel_overlap) / len(artist_words)
        if ratio >= 0.5:
            return int(70 + ratio * 20), f"channel word match: {', '.join(sorted(channel_overlap))}"

    # Check overlap with title
    title_overlap = artist_words & title_words
    if title_overlap:
        ratio = len(title_overlap) / len(artist_words)
        if ratio >= 0.5:
            return int(60 + ratio * 20), f"title word match: {', '.join(sorted(title_overlap))}"

    # Partial word overlap
    all_video_words = title_words | channel_words
    any_overlap = artist_words & all_video_words
    if any_overlap:
        ratio = len(any_overlap) / len(artist_words)
        return int(30 + ratio * 30), f"partial match: {', '.join(sorted(any_overlap))}"

    return 5, "no match between artist name and video"


# --- YouTube oEmbed fetching ---

def fetch_video_info(youtube_id):
    """Fetch video title and channel from YouTube oEmbed. Returns dict or None."""
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={youtube_id}&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LocalSoundcheck-Audit/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return {
                "title": data.get("title", ""),
                "channel": data.get("author_name", ""),
            }
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"title": None, "channel": None, "error": "video_not_found"}
        return {"title": None, "channel": None, "error": f"http_{e.code}"}
    except Exception as e:
        return {"title": None, "channel": None, "error": str(e)}


# --- Audit logic ---

def audit_venue(filepath):
    """Audit all YouTube matches for a single venue file."""
    with open(filepath) as f:
        data = json.load(f)

    # Handle both formats: {"shows": [...]} or bare [...]
    shows = data.get("shows", data) if isinstance(data, dict) else data
    venue_name = os.path.basename(filepath).replace("shows-", "").replace(".json", "")
    results = []

    for show in shows:
        if show.get("expired"):
            continue

        # Audit headliner
        artist = show.get("artist", "")
        youtube_id = show.get("youtube_id")

        entry = {
            "artist": artist,
            "date": show.get("date", ""),
            "venue": show.get("venue", ""),
            "role": "headliner",
            "youtube_id": youtube_id,
        }

        if youtube_id:
            info = fetch_video_info(youtube_id)
            entry["video_title"] = info.get("title")
            entry["video_channel"] = info.get("channel")
            entry["error"] = info.get("error")

            if info.get("error"):
                entry["confidence"] = 0
                entry["confidence_tier"] = "error"
                entry["explanation"] = info["error"]
            else:
                score, explanation = score_match(artist, info["title"], info["channel"])
                entry["confidence"] = score
                entry["confidence_tier"] = (
                    "high" if score >= 70 else
                    "medium" if score >= 40 else
                    "low"
                )
                entry["explanation"] = explanation

            time.sleep(0.3)  # Rate limiting
        else:
            entry["confidence"] = None
            entry["confidence_tier"] = "no_video"
            entry["explanation"] = "no youtube_id assigned"

        results.append(entry)

        # Audit opener
        opener = show.get("opener")
        opener_id = show.get("opener_youtube_id")

        if opener:
            opener_entry = {
                "artist": opener,
                "date": show.get("date", ""),
                "venue": show.get("venue", ""),
                "role": "opener",
                "youtube_id": opener_id,
            }

            if opener_id:
                info = fetch_video_info(opener_id)
                opener_entry["video_title"] = info.get("title")
                opener_entry["video_channel"] = info.get("channel")
                opener_entry["error"] = info.get("error")

                if info.get("error"):
                    opener_entry["confidence"] = 0
                    opener_entry["confidence_tier"] = "error"
                    opener_entry["explanation"] = info["error"]
                else:
                    # For openers with multiple names, check first name
                    opener_name = opener.split(",")[0].strip()
                    score, explanation = score_match(opener_name, info["title"], info["channel"])
                    opener_entry["confidence"] = score
                    opener_entry["confidence_tier"] = (
                        "high" if score >= 70 else
                        "medium" if score >= 40 else
                        "low"
                    )
                    opener_entry["explanation"] = explanation

                time.sleep(0.3)
            else:
                opener_entry["confidence"] = None
                opener_entry["confidence_tier"] = "no_video"
                opener_entry["explanation"] = "no opener_youtube_id assigned"

            results.append(opener_entry)

    return venue_name, results


def compute_stats(results):
    """Compute summary statistics from audit results."""
    with_video = [r for r in results if r["youtube_id"]]
    no_video = [r for r in results if not r["youtube_id"]]

    high = [r for r in with_video if r["confidence_tier"] == "high"]
    medium = [r for r in with_video if r["confidence_tier"] == "medium"]
    low = [r for r in with_video if r["confidence_tier"] == "low"]
    errors = [r for r in with_video if r["confidence_tier"] == "error"]

    total = len(results)
    return {
        "total_entries": total,
        "with_video": len(with_video),
        "no_video": len(no_video),
        "high_confidence": len(high),
        "medium_confidence": len(medium),
        "low_confidence": len(low),
        "errors": len(errors),
        "accuracy_rate": round(len(high) / len(with_video) * 100, 1) if with_video else 0,
        "avg_confidence": round(sum(r["confidence"] for r in with_video if r["confidence"] is not None) / len(with_video), 1) if with_video else 0,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Audit YouTube match accuracy")
    parser.add_argument("--venue", help="Audit a single venue (e.g. catscradle)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be audited")
    args = parser.parse_args()

    # Find venue files
    if args.venue:
        pattern = f"{DATA_DIR}/shows-{args.venue}.json"
        files = glob.glob(pattern)
        if not files:
            print(f"No file found matching {pattern}")
            sys.exit(1)
    else:
        files = sorted(glob.glob(f"{DATA_DIR}/shows-*.json"))

    if not files:
        print("No show data files found.")
        sys.exit(1)

    if args.dry_run:
        print(f"Would audit {len(files)} venue(s):")
        for f in files:
            print(f"  {f}")
        sys.exit(0)

    # Run audit
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    all_results = {}
    all_entries = []

    print(f"YouTube Match Accuracy Audit — {timestamp}")
    print("=" * 60)

    for filepath in files:
        venue_name, results = audit_venue(filepath)
        stats = compute_stats(results)
        all_results[venue_name] = {"stats": stats, "entries": results}
        all_entries.extend(results)

        # Print venue summary
        print(f"\n{venue_name}: {stats['with_video']} videos checked")
        print(f"  High: {stats['high_confidence']}  Medium: {stats['medium_confidence']}  Low: {stats['low_confidence']}  Error: {stats['errors']}  No video: {stats['no_video']}")
        print(f"  Accuracy (high confidence): {stats['accuracy_rate']}%  Avg score: {stats['avg_confidence']}")

        # Show problems
        for entry in results:
            if entry.get("confidence_tier") in ("low", "error"):
                print(f"  ⚠ {entry['role'].upper()} {entry['artist']}")
                print(f"    Video: {entry.get('video_title', 'N/A')} — {entry.get('video_channel', 'N/A')}")
                print(f"    Score: {entry['confidence']} ({entry['explanation']})")

    # Overall summary
    overall = compute_stats(all_entries)
    print("\n" + "=" * 60)
    print(f"OVERALL: {overall['with_video']} videos across {len(files)} venues")
    print(f"  High: {overall['high_confidence']}  Medium: {overall['medium_confidence']}  Low: {overall['low_confidence']}  Error: {overall['errors']}  No video: {overall['no_video']}")
    print(f"  Accuracy (high confidence): {overall['accuracy_rate']}%")
    print(f"  Average confidence score: {overall['avg_confidence']}")

    # Save audit file
    os.makedirs(AUDIT_DIR, exist_ok=True)
    audit_file = os.path.join(AUDIT_DIR, f"{timestamp}.json")
    audit_data = {
        "timestamp": datetime.now().isoformat(),
        "overall": overall,
        "venues": all_results,
    }

    with open(audit_file, "w") as f:
        json.dump(audit_data, f, indent=2)

    print(f"\nAudit saved to {audit_file}")


if __name__ == "__main__":
    main()
