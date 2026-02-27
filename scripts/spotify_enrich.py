#!/usr/bin/env python3
"""
Spotify Artist Enrichment — standalone enrichment step for the video pipeline.

Looks up each artist on Spotify to confirm they exist and stores metadata
(popularity, genres, followers). Provides identity confirmation and scale
context for the video verifier.

Runs after scraping and before video verification in the nightly pipeline.
Results cached in qa/spotify_cache.json with a 30-day TTL.

Usage:
    python scripts/spotify_enrich.py                    # Enrich all artists
    python scripts/spotify_enrich.py --artist "Heated"  # Single artist lookup
    python scripts/spotify_enrich.py --dry-run           # Preview without saving
    python scripts/spotify_enrich.py --force             # Ignore cache, re-fetch all
"""

import os
import sys
import json
import re
import argparse
from datetime import datetime, timedelta

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from scrapers.utils import load_env_var, normalize as _normalize, name_similarity

CACHE_PATH = os.path.join(_PROJECT_ROOT, "qa", "spotify_cache.json")
CACHE_TTL_DAYS = 30


# --- Auth ---

def load_spotify_credentials():
    """Load Spotify client credentials from environment or .env file."""
    client_id = load_env_var("SPOTIFY_CLIENT_ID")
    client_secret = load_env_var("SPOTIFY_CLIENT_SECRET")
    if client_id and client_secret:
        return client_id, client_secret
    return None, None


def get_access_token(client_id, client_secret):
    """Get Spotify access token via Client Credentials flow."""
    import requests
    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"  Error: Spotify auth failed ({resp.status_code}): {resp.text}")
        return None
    return resp.json().get("access_token")


# --- Cache ---

def load_cache():
    """Load the Spotify enrichment cache."""
    try:
        with open(CACHE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache):
    """Save the Spotify enrichment cache."""
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)
        f.write("\n")


def is_cache_fresh(entry):
    """Check if a cache entry is within TTL."""
    enriched = entry.get("enriched_date")
    if not enriched:
        return False
    try:
        enriched_dt = datetime.fromisoformat(enriched)
        return datetime.now().astimezone() - enriched_dt < timedelta(days=CACHE_TTL_DAYS)
    except (ValueError, TypeError):
        return False


# --- Spotify API ---

def search_artist(artist_name, token):
    """Search Spotify for an artist. Returns best match or None."""
    import requests
    resp = requests.get(
        "https://api.spotify.com/v1/search",
        params={"q": artist_name, "type": "artist", "limit": 5},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"  Warning: Spotify search failed for '{artist_name}' ({resp.status_code})")
        return None

    artists = resp.json().get("artists", {}).get("items", [])
    if not artists:
        return None

    # Pick best match by name similarity
    best = None
    best_score = 0.0
    for a in artists:
        score = name_similarity(artist_name, a["name"])
        # Boost score for higher-popularity artists when names are close
        if score >= 0.8:
            score += a.get("popularity", 0) / 1000  # tiny boost, max +0.1
        if score > best_score:
            best_score = score
            best = a

    # Require higher similarity for multi-word names (avoids "COMMON WOMAN CABARET" → "Common")
    min_score = 0.7 if len(artist_name.split()) >= 3 else 0.5
    if best and best_score >= min_score:
        match_type = "exact" if best_score >= 1.0 else "close" if best_score >= 0.8 else "partial"
        return {
            "spotify_id": best["id"],
            "spotify_name": best["name"],
            "popularity": best.get("popularity", 0),
            "followers": best.get("followers", {}).get("total", 0),
            "genres": best.get("genres", []),
            "match_confidence": match_type,
            "match_score": round(best_score, 3),
        }

    return None


# --- Show data ---

def collect_artists(single_artist=None):
    """
    Collect unique artists from all show data files.
    Returns dict: {artist_name: [{venue, date, youtube_id, video_title}, ...]}
    """
    if single_artist:
        return {single_artist: []}

    data_dir = os.path.join(_PROJECT_ROOT, "data")
    artists = {}

    for filename in sorted(os.listdir(data_dir)):
        if not (filename.startswith("shows-") and filename.endswith(".json")):
            continue
        filepath = os.path.join(data_dir, filename)
        try:
            with open(filepath) as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            continue

        shows = data.get("shows", data) if isinstance(data, dict) else data
        for show in shows:
            if not isinstance(show, dict):
                continue
            for name_key, id_key in [("artist", "youtube_id"), ("opener", "opener_youtube_id")]:
                name = show.get(name_key, "")
                if not name:
                    continue
                if name not in artists:
                    artists[name] = []
                artists[name].append({
                    "venue": show.get("venue", "Unknown"),
                    "date": show.get("date", "TBD"),
                    "youtube_id": show.get(id_key),
                })

    return artists


# --- Main enrichment ---

def enrich_artist(artist_name, token, cache, force=False):
    """
    Enrich a single artist with Spotify data.
    Returns the cache entry (new or existing).
    """
    # Check cache
    if not force and artist_name in cache and is_cache_fresh(cache[artist_name]):
        return cache[artist_name], False  # (entry, was_fetched)

    # Search Spotify
    result = search_artist(artist_name, token)

    if result:
        entry = {
            "spotify_id": result["spotify_id"],
            "spotify_name": result["spotify_name"],
            "popularity": result["popularity"],
            "followers": result["followers"],
            "genres": result["genres"],
            "enriched_date": datetime.now().astimezone().isoformat(),
            "match_confidence": result["match_confidence"],
            "match_score": result["match_score"],
        }
    else:
        entry = {
            "spotify_id": None,
            "spotify_name": None,
            "enriched_date": datetime.now().astimezone().isoformat(),
            "match_confidence": "no_match",
            "note": "No Spotify artist found",
        }

    return entry, True  # (entry, was_fetched)


def main():
    parser = argparse.ArgumentParser(description="Spotify artist enrichment")
    parser.add_argument("--artist", help="Enrich a single artist by name")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without saving cache")
    parser.add_argument("--force", action="store_true",
                        help="Ignore cache TTL, re-fetch all")
    args = parser.parse_args()

    print("=" * 50)
    print("LOCAL SOUNDCHECK — SPOTIFY ENRICHMENT")
    print("=" * 50)

    # Auth
    client_id, client_secret = load_spotify_credentials()
    if not client_id or not client_secret:
        print("Error: No Spotify credentials found.")
        print("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in .env or environment.")
        sys.exit(1)

    token = get_access_token(client_id, client_secret)
    if not token:
        print("Error: Could not authenticate with Spotify.")
        sys.exit(1)
    print("  Authenticated with Spotify API")

    # Load cache and show data
    cache = load_cache()
    artists = collect_artists(single_artist=args.artist)
    print(f"  {len(artists)} unique artists to process")
    print(f"  {len(cache)} entries in cache")

    # Enrich
    stats = {"fetched": 0, "cached": 0, "confirmed": 0, "mismatched": 0, "not_found": 0}

    for artist_name, shows in sorted(artists.items()):
        entry, was_fetched = enrich_artist(artist_name, token, cache, force=args.force)

        if was_fetched:
            stats["fetched"] += 1
            cache[artist_name] = entry
            if entry.get("spotify_id"):
                print(f"  + {artist_name} → {entry['spotify_name']} "
                      f"(pop={entry['popularity']}, followers={entry['followers']:,}, "
                      f"match={entry['match_confidence']})")
            else:
                stats["not_found"] += 1
                print(f"  - {artist_name} → no Spotify match")
        else:
            stats["cached"] += 1

        # Track stats
        if entry.get("spotify_id") and was_fetched:
            if entry.get("match_confidence") in ("exact", "close"):
                stats["confirmed"] += 1

    # Save
    if not args.dry_run:
        save_cache(cache)
        print(f"\n  Saved {len(cache)} entries to {os.path.relpath(CACHE_PATH, _PROJECT_ROOT)}")
    else:
        print("\n  Dry run — cache not saved")

    # Summary
    print(f"\n{'=' * 50}")
    print(f"  API lookups: {stats['fetched']} (cached: {stats['cached']})")
    print(f"  Found on Spotify: {stats['fetched'] - stats['not_found']}")
    print(f"  Not found: {stats['not_found']}")
    print(f"  Strong matches: {stats['confirmed']}")
    print(f"{'=' * 50}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
