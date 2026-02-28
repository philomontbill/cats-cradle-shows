#!/usr/bin/env python3
"""
Base Scraper class with shared functionality for all venue scrapers.
Each venue scraper inherits from this and implements venue-specific logic.
"""

import os
import sys
import requests
import json
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote_plus

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

from scrapers.utils import load_env_var, normalize_artist


class BaseScraper:
    """Base class for all venue scrapers with shared functionality."""

    # Subclasses should override these
    venue_name = "Unknown Venue"
    venue_location = "Unknown Location"
    venue_website = "https://example.com"
    output_filename = "shows.json"

    # Confidence thresholds
    CONFIDENCE_ACCEPT = 70   # Auto-accept match
    CONFIDENCE_FLAG = 40     # Flag for manual review
    # Below 40 = skip (no video assigned)

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.overrides = self._load_overrides()
        self.api_key = self._load_api_key()
        self.match_log = []
        print(f"{self.venue_name} Show Scraper")
        print("=" * 40)
        if self.api_key:
            print("YouTube API: enabled")
        else:
            print("YouTube API: not configured (falling back to scraping)")

    def _load_overrides(self):
        """Load manual YouTube overrides from overrides.json"""
        try:
            with open(os.path.join(_SCRIPT_DIR, 'overrides.json'), 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"artist_youtube": {}, "opener_youtube": {}}

    def _load_api_key(self):
        """Load YouTube API key from environment or .env file."""
        return load_env_var('YOUTUBE_API_KEY')

    def scrape_shows(self):
        """Main scraping function - subclasses must implement."""
        raise NotImplementedError("Subclasses must implement scrape_shows()")

    # --- Artist name cleaning ---

    # Event-name keywords — if the artist field contains these, it's not a band
    EVENT_KEYWORDS = re.compile(
        r'\b(Cabaret|Burlesque|Dance Party|Drag .* Rewind|Afrocentric|'
        r'Festival|Showcase|Series|Open Mic|Karaoke|Trivia|Quizzo|'
        r'Comedy Night|DJ Night|Disco Night|Prom|Blowout|Graduation|'
        r'Takeover|Cover Up|Rehearsal|Jamz|Hosted By|Honoring|'
        r'Songwriters Show|Blends With Friends|Tribute Band|GrrrlBands|'
        r'It.?s A \d+.?s Party|Party Iconic|Photobooth)\b'
        r'|^DJs?:',  # Lines starting with "DJ:" or "DJs:"
        re.IGNORECASE
    )

    def _clean_artist_name(self, artist_name):
        """Clean artist name for YouTube search. Returns None for event names."""
        if not artist_name or len(artist_name) < 2:
            return None
        # Check event keywords on the original name first (catches "DJs:", "GrrrlBands:", etc.)
        if self.EVENT_KEYWORDS.search(artist_name):
            return None
        # Case-sensitive: "RIP ..." or "R.I.P." at start = memorial event, not a band
        # (case-sensitive to avoid matching bands like "Rip Tide", "Ripper")
        if re.match(r'^R\.?I\.?P\.?\s', artist_name):
            return None
        # Strip "Presents" and everything after it (band name is before it)
        clean = re.sub(r'\s+Presents\b.*$', '', artist_name, flags=re.IGNORECASE)
        # Strip tour/event suffixes after colon ("Kevin Devine: 20 Years..." → "Kevin Devine")
        clean = re.sub(r':.*$', '', clean)
        # Strip tour/event suffixes (with or without dash prefix)
        clean = re.sub(r'\s*[-–—]\s*(Tour|US Tour|Headline Tour|Wither Tour|Live|Concert|Show|Anniversary|Tribute|Benefit|Dance|Jam|Bash|Album Release|The \w+ Tour).*$', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\s+US Tour\b.*$', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\s+Album Release\b.*$', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\s*\d+(st|nd|rd|th)\s+Annual.*$', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\s*\([^)]*\)', '', clean)
        # Strip "feat." / "Feat:" suffixes
        clean = re.sub(r'\s+feat[.:]\s+.*$', '', clean, flags=re.IGNORECASE)
        # Split multi-artist: take first artist before comma, " / ", or "w/"
        clean = re.sub(r'\s+w/\s+.*$', '', clean)
        clean = re.sub(r',.*$', '', clean)
        clean = re.sub(r'\s+/\s+.*$', '', clean)  # " / " = band separator; "Model/Actriz" stays intact
        clean = clean.strip()
        return clean if len(clean) >= 2 else None

    def _normalize(self, name):
        """Normalize a name for comparison."""
        return normalize_artist(name)

    def _word_set(self, text):
        """Get set of meaningful words (3+ chars) from text."""
        return set(w for w in self._normalize(text).split() if len(w) >= 3)

    # --- Confidence scoring ---

    def _score_match(self, artist_name, video_title, channel_name):
        """
        Score how well a YouTube video matches an artist name.
        Returns (score 0-100, explanation).

        Channel name match is the strongest signal — it means the video
        is on the artist's own channel. Title-only matches are weaker
        because common words (Nothing, Heated, Drug Dealer) appear in
        many unrelated song titles.
        """
        if not artist_name or (not video_title and not channel_name):
            return 0, "no data to compare"

        artist_norm = self._normalize(artist_name)
        title_norm = self._normalize(video_title or "")
        channel_norm = self._normalize(channel_name or "")

        if not artist_norm:
            return 0, "no meaningful artist name"

        artist_words = self._word_set(artist_name)
        channel_words = self._word_set(channel_name or "")
        title_words = self._word_set(video_title or "")
        is_single_word = len(artist_words) <= 1

        # --- CHANNEL NAME MATCHES (strong signal) ---

        # Full artist name found in channel name
        if artist_norm in channel_norm:
            return 95, "artist name found in channel name"

        # Channel name found in artist name
        if channel_norm and len(channel_norm) >= 3 and channel_norm in artist_norm:
            return 85, "channel name found in artist name"

        # Strong channel word overlap
        channel_overlap = artist_words & channel_words
        if channel_overlap:
            ratio = len(channel_overlap) / len(artist_words)
            if ratio >= 0.5:
                return int(70 + ratio * 20), f"channel match: {', '.join(sorted(channel_overlap))}"

        # --- TITLE-ONLY MATCHES (weaker, needs caution) ---

        # For single-word artist names, title matches are unreliable
        # "Nothing" matches "I Have Nothing", "Heated" matches "HEATED" by Beyoncé
        if is_single_word:
            # Only accept title match if it starts with the artist name
            if title_norm.startswith(artist_norm):
                return 55, "single-word artist at start of title (no channel match)"
            # Otherwise very low confidence
            title_overlap = artist_words & title_words
            if title_overlap:
                return 20, f"single-word title match (ambiguous): {', '.join(sorted(title_overlap))}"
            return 5, "no match"

        # Multi-word artist: full name in title is decent signal
        if artist_norm in title_norm:
            return 75, "multi-word artist name found in video title"

        # Multi-word artist: word overlap with title
        title_overlap = artist_words & title_words
        if title_overlap:
            ratio = len(title_overlap) / len(artist_words)
            if ratio >= 0.5:
                return int(50 + ratio * 20), f"title match: {', '.join(sorted(title_overlap))}"

        # --- PARTIAL MATCHES (low confidence) ---

        all_words = title_words | channel_words
        any_overlap = artist_words & all_words
        if any_overlap:
            ratio = len(any_overlap) / len(artist_words)
            return int(20 + ratio * 25), f"partial: {', '.join(sorted(any_overlap))}"

        return 5, "no match"

    # --- YouTube search methods ---

    def get_youtube_id(self, artist_name, is_opener=False):
        """Get YouTube video ID for an artist, checking overrides first."""
        if not artist_name:
            return None

        # Check overrides first (try raw name, then cleaned name)
        override_key = 'opener_youtube' if is_opener else 'artist_youtube'
        overrides = self.overrides.get(override_key, {})

        if artist_name in overrides:
            override_val = overrides[artist_name]
            self._log_match(artist_name, override_val, 100, "override", "manual override", is_opener)
            return override_val

        # Clean name for search (strips tour info, multi-artist, event names)
        search_name = self._clean_artist_name(artist_name)
        if not search_name:
            self._log_match(artist_name, None, 0, "skip", "event name or invalid", is_opener)
            return None

        # Check overrides with cleaned name too
        if search_name in overrides:
            override_val = overrides[search_name]
            self._log_match(artist_name, override_val, 100, "override", "manual override (cleaned name)", is_opener)
            return override_val

        # Use API if available, otherwise fall back to scraping
        if self.api_key:
            return self._search_youtube_api(search_name, is_opener)
        else:
            return self._search_youtube_scrape(search_name, is_opener)

    def _search_youtube_api(self, artist_name, is_opener=False):
        """Search YouTube Data API with confidence scoring. Expects pre-cleaned name."""
        if not artist_name or len(artist_name) < 2:
            self._log_match(artist_name, None, 0, "skip", "name too short or invalid", is_opener)
            return None

        try:
            # Search with Music category filter
            query = f"{artist_name} official music video"
            url = (
                f"https://www.googleapis.com/youtube/v3/search"
                f"?part=snippet"
                f"&q={quote_plus(query)}"
                f"&type=video"
                f"&videoCategoryId=10"
                f"&maxResults=5"
                f"&key={self.api_key}"
            )

            resp = requests.get(url, timeout=10)
            if resp.status_code == 403:
                print(f"    ⚠ YouTube API quota exceeded, falling back to scraping")
                return self._search_youtube_scrape(artist_name, is_opener)
            if resp.status_code != 200:
                print(f"    ⚠ YouTube API error {resp.status_code}")
                return self._search_youtube_scrape(artist_name, is_opener)

            data = resp.json()
            items = data.get("items", [])

            if not items:
                # Retry without Music category filter
                url_no_cat = (
                    f"https://www.googleapis.com/youtube/v3/search"
                    f"?part=snippet"
                    f"&q={quote_plus(artist_name + ' band music')}"
                    f"&type=video"
                    f"&maxResults=5"
                    f"&key={self.api_key}"
                )
                resp2 = requests.get(url_no_cat, timeout=10)
                if resp2.status_code == 200:
                    items = resp2.json().get("items", [])

            if not items:
                self._log_match(artist_name, None, 0, "no_results", "no YouTube results found", is_opener)
                return None

            # Score each candidate and pick the best
            best_id = None
            best_score = 0
            best_explanation = ""
            best_title = ""
            best_channel = ""

            for item in items:
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId")
                title = snippet.get("title", "")
                channel = snippet.get("channelTitle", "")

                score, explanation = self._score_match(artist_name, title, channel)

                # Bonus: if found in Music category search, add 5 points
                score = min(score + 5, 100)

                if score > best_score:
                    best_score = score
                    best_id = video_id
                    best_explanation = explanation
                    best_title = title
                    best_channel = channel

            # Apply confidence threshold
            if best_score >= self.CONFIDENCE_ACCEPT:
                tier = "accept"
                result_id = best_id
            elif best_score >= self.CONFIDENCE_FLAG:
                tier = "flag"
                result_id = best_id  # Accept but flag for review
            else:
                tier = "skip"
                result_id = None

            self._log_match(
                artist_name, result_id, best_score, tier,
                f"{best_explanation} | video: {best_title} | channel: {best_channel}",
                is_opener
            )

            if tier == "flag":
                print(f"    ⚠ Flagged ({best_score}): {best_title} — {best_channel}")

            return result_id

        except Exception as e:
            print(f"    ⚠ API error: {e}")
            return self._search_youtube_scrape(artist_name, is_opener)

    def _search_youtube_scrape(self, artist_name, is_opener=False):
        """Fallback: Search YouTube by scraping search results. Expects pre-cleaned name."""
        try:
            if not artist_name or len(artist_name) < 2:
                return None

            search_queries = [
                f"{artist_name} band official video",
                f"{artist_name} band music",
                f"{artist_name} official music video",
            ]

            for query_text in search_queries:
                query = quote_plus(query_text)
                url = f"https://www.youtube.com/results?search_query={query}"

                response = requests.get(url, headers=self.headers, timeout=10)

                if response.status_code == 200:
                    patterns = [
                        r'"videoId":"([a-zA-Z0-9_-]{11})"',
                        r'/watch\?v=([a-zA-Z0-9_-]{11})',
                    ]

                    for pattern in patterns:
                        matches = re.findall(pattern, response.text)
                        if matches:
                            video_id = matches[0]
                            self._log_match(artist_name, video_id, None, "scrape_fallback", "scraped (no confidence score)", is_opener)
                            return video_id

                time.sleep(0.3)

            self._log_match(artist_name, None, 0, "no_results", "scrape fallback found nothing", is_opener)
            return None

        except Exception:
            return None

    # --- Smart search: reuse existing high-confidence matches ---

    def _load_existing_matches(self):
        """Load artist->youtube_id mappings from the previous scrape output."""
        matches = {}
        try:
            with open(self.output_filename) as f:
                data = json.load(f)
            shows = data.get("shows", data) if isinstance(data, dict) else data
            for show in shows:
                if isinstance(show, dict):
                    artist = show.get("artist", "")
                    yt_id = show.get("youtube_id")
                    if artist and yt_id:
                        matches[artist] = yt_id
                    opener = show.get("opener", "")
                    opener_id = show.get("opener_youtube_id")
                    if opener and opener_id:
                        matches[opener] = opener_id
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return matches

    def _load_audit_scores(self):
        """Load confidence scores from the latest audit file."""
        scores = {}
        audit_dir = os.path.join(_PROJECT_ROOT, "qa", "audits")
        try:
            audit_files = sorted(
                [f for f in os.listdir(audit_dir) if f.endswith(".json")],
                reverse=True
            )
            if not audit_files:
                return scores
            with open(os.path.join(audit_dir, audit_files[0])) as f:
                audit = json.load(f)
            for venue_data in audit.get("venues", {}).values():
                for entry in venue_data.get("entries", []):
                    artist = entry.get("artist", "")
                    yt_id = entry.get("youtube_id")
                    confidence = entry.get("confidence")
                    if artist and yt_id and confidence is not None:
                        scores[artist] = {
                            "youtube_id": yt_id,
                            "confidence": confidence,
                            "tier": entry.get("confidence_tier", "unknown"),
                        }
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return scores

    def _load_video_states(self):
        """Load all rejections from qa/video_states.json.

        Returns a dict of artist_name -> rejected_date for all rejected artists.
        Rejected artists are permanently skipped — no automatic re-search.
        Daily reports surface missing videos for manual review.
        """
        rejections = {}
        states_path = os.path.join(_PROJECT_ROOT, "qa", "video_states.json")
        try:
            with open(states_path) as f:
                states = json.load(f)
            for artist, state in states.items():
                if not isinstance(state, dict):
                    continue
                if state.get("status") != "rejected":
                    continue
                rejections[artist] = state.get("rejected_date", "")
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return rejections

    def _should_search(self, artist_name, existing_matches, audit_scores,
                       recent_rejections=None):
        """
        Decide whether to spend an API call on this artist.
        Returns (should_search: bool, existing_id: str or None, reason: str).
        """
        if not artist_name:
            return False, None, "no artist name"

        # Skip artists rejected by the verifier — no automatic re-search
        if recent_rejections and artist_name in recent_rejections:
            return False, None, "rejected by verifier (permanent skip)"

        # Always search if no existing match
        if artist_name not in existing_matches:
            return True, None, "new artist"

        existing_id = existing_matches[artist_name]

        # Check audit confidence for existing match
        audit = audit_scores.get(artist_name)
        if audit and audit["confidence"] is not None:
            if audit["confidence"] >= self.CONFIDENCE_ACCEPT:
                return False, existing_id, f"existing high confidence ({audit['confidence']})"
            else:
                return True, existing_id, f"existing low confidence ({audit['confidence']}), re-searching"

        # Has an existing match but no audit score — keep it, don't waste a search
        return False, existing_id, "existing match (no audit score, keeping)"

    # --- Match logging ---

    def _log_match(self, artist_name, youtube_id, confidence, tier, explanation, is_opener=False):
        """Log a match result for QA review."""
        self.match_log.append({
            "artist": artist_name,
            "role": "opener" if is_opener else "headliner",
            "youtube_id": youtube_id,
            "confidence": confidence,
            "tier": tier,
            "explanation": explanation,
            "timestamp": datetime.now().isoformat(),
            "venue": self.venue_name,
        })

    def _save_match_log(self):
        """Save match log to qa/match_log.json (append to existing)."""
        if not self.match_log:
            return

        log_path = os.path.join(_PROJECT_ROOT, "qa", "match_log.json")
        existing = []
        try:
            with open(log_path) as f:
                existing = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        existing.extend(self.match_log)

        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w") as f:
            json.dump(existing, f, indent=2)

        accepted = sum(1 for m in self.match_log if m["tier"] == "accept")
        flagged = sum(1 for m in self.match_log if m["tier"] == "flag")
        skipped = sum(1 for m in self.match_log if m["tier"] == "skip")
        overrides = sum(1 for m in self.match_log if m["tier"] == "override")
        print(f"\nMatch log: {accepted} accepted, {flagged} flagged, {skipped} skipped, {overrides} overrides")

    # --- Show processing ---

    def save_json(self, shows):
        """Save shows to JSON file."""
        data = {
            'venue': {
                'name': self.venue_name,
                'location': self.venue_location,
                'website': self.venue_website
            },
            'shows': shows,
            'total_shows': len(shows),
            'shows_with_video': sum(1 for s in shows if s.get('youtube_id')),
            'shows_with_image': sum(1 for s in shows if s.get('image')),
            'last_updated': datetime.now().isoformat()
        }

        with open(self.output_filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nSaved {len(shows)} shows to {self.output_filename}")
        print(f"  - {data['shows_with_video']} have YouTube videos")
        print(f"  - {data['shows_with_image']} have images")

    def format_date_standard(self, date_str, input_format=None):
        """Convert various date formats to standard 'Sat, Feb 07' format."""
        try:
            today = datetime.now().date()
            current_year = today.year

            if input_format:
                try:
                    parsed = datetime.strptime(date_str, input_format)
                    if parsed.year == 1900:
                        parsed = parsed.replace(year=current_year)
                        if parsed.date() < today:
                            parsed = parsed.replace(year=current_year + 1)
                    return parsed.strftime("%a, %b %d")
                except ValueError:
                    pass

            formats = [
                "%m/%d/%Y",
                "%Y-%m-%d",
                "%A %B %d",
                "%A %b %d",
                "%B %d %Y",
                "%b %d %Y",
                "%B %d",
                "%b %d"
            ]

            clean = re.sub(r',\s*', ' ', date_str).strip()

            for fmt in formats:
                try:
                    parsed = datetime.strptime(clean, fmt)
                    if parsed.year == 1900:
                        parsed = parsed.replace(year=current_year)
                        if parsed.date() < today:
                            parsed = parsed.replace(year=current_year + 1)
                    return parsed.strftime("%a, %b %d")
                except ValueError:
                    continue

            return date_str
        except:
            return date_str

    def sort_shows_by_date(self, shows):
        """Sort shows chronologically."""
        current_year = datetime.now().year

        def date_key(show):
            date_str = show.get('date', 'TBD')
            if date_str == 'TBD':
                return datetime(2099, 12, 31)

            try:
                parsed = datetime.strptime(f"{date_str}, {current_year}", "%a, %b %d, %Y")
                return parsed
            except:
                return datetime(2099, 12, 31)

        return sorted(shows, key=date_key)

    def process_shows_with_youtube(self, shows, limit=25):
        """Add YouTube IDs to shows list with progress output."""
        processed = []
        show_overrides = self.overrides.get('show_overrides', {})

        # Load existing matches, audit scores, and recent rejections for smart filtering
        existing_matches = self._load_existing_matches()
        audit_scores = self._load_audit_scores()
        recent_rejections = self._load_video_states()
        api_calls = 0
        reused = 0

        if existing_matches:
            print(f"Loaded {len(existing_matches)} existing matches")
        if audit_scores:
            print(f"Loaded {len(audit_scores)} audit scores")
        if recent_rejections:
            print(f"Loaded {len(recent_rejections)} recent rejections (skipping)")

        for i, show in enumerate(shows[:limit], 1):
            # Apply show-level overrides (e.g. festival events with wrong artist names)
            scraped_artist = show.get('artist', '')
            if scraped_artist in show_overrides:
                override = show_overrides[scraped_artist]
                show['artist'] = override.get('artist', show['artist'])
                show['opener'] = override.get('opener', show.get('opener'))
                if 'notice' in override:
                    show['notice'] = override['notice']

            artist = show.get('artist', '')
            opener = show.get('opener', '')

            # Smart filter: check if we need to search for headliner
            should_search, existing_id, reason = self._should_search(
                artist, existing_matches, audit_scores, recent_rejections
            )
            if should_search:
                show['youtube_id'] = self.get_youtube_id(artist)
                api_calls += 1
            else:
                show['youtube_id'] = existing_id
                self._log_match(artist, existing_id, None, "reused", reason)
                reused += 1

            # Smart filter: check if we need to search for opener
            if opener:
                should_search_opener, existing_opener_id, opener_reason = self._should_search(
                    opener, existing_matches, audit_scores, recent_rejections
                )
                if should_search_opener:
                    show['opener_youtube_id'] = self.get_youtube_id(opener, is_opener=True)
                    api_calls += 1
                else:
                    show['opener_youtube_id'] = existing_opener_id
                    self._log_match(opener, existing_opener_id, None, "reused", opener_reason, is_opener=True)
                    reused += 1

            # Progress output
            print(f"[{i}/{min(len(shows), limit)}] {artist} ({show.get('date', 'TBD')})")
            if opener:
                opener_display = opener[:40] + ('...' if len(opener) > 40 else '')
                print(f"        Opener: {opener_display}")
            if show.get('youtube_id'):
                status = "reused" if not should_search else "searched"
                print(f"        YouTube: {show['youtube_id']} ({status})")

            processed.append(show)
            if should_search:
                time.sleep(0.3)

        # Save match log after processing
        self._save_match_log()
        print(f"\nAPI calls: {api_calls} | Reused: {reused}")

        return processed
