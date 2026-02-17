#!/usr/bin/env python3
"""
Base Scraper class with shared functionality for all venue scrapers.
Each venue scraper inherits from this and implements venue-specific logic.
"""

import os
import requests
import json
import re
import time
from datetime import datetime
from urllib.parse import quote_plus

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class BaseScraper:
    """Base class for all venue scrapers with shared functionality."""

    # Subclasses should override these
    venue_name = "Unknown Venue"
    venue_location = "Unknown Location"
    venue_website = "https://example.com"
    output_filename = "shows.json"

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.overrides = self._load_overrides()
        print(f"{self.venue_name} Show Scraper")
        print("=" * 40)

    def _load_overrides(self):
        """Load manual YouTube overrides from overrides.json"""
        try:
            with open(os.path.join(_SCRIPT_DIR, 'overrides.json'), 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"artist_youtube": {}, "opener_youtube": {}}

    def scrape_shows(self):
        """Main scraping function - subclasses must implement."""
        raise NotImplementedError("Subclasses must implement scrape_shows()")

    def get_youtube_id(self, artist_name, is_opener=False):
        """Get YouTube video ID for an artist, checking overrides first."""
        if not artist_name:
            return None

        # Check overrides first
        override_key = 'opener_youtube' if is_opener else 'artist_youtube'
        overrides = self.overrides.get(override_key, {})

        # For openers, just use first name if comma-separated
        search_name = artist_name.split(',')[0].strip() if is_opener else artist_name

        if search_name in overrides:
            return overrides[search_name]

        return self._search_youtube(search_name)

    def _search_youtube(self, artist_name):
        """Search YouTube for artist's music by scraping search results."""
        try:
            if not artist_name or len(artist_name) < 2:
                return None

            # Clean up artist name for search
            clean_name = re.sub(r'\s*[-–]\s*(Tour|Live|Concert|Show|Anniversary|Tribute|Benefit|Dance|Jam|Bash).*$', '', artist_name, flags=re.IGNORECASE)
            clean_name = re.sub(r'\s*\d+(st|nd|rd|th)\s+Annual.*$', '', clean_name, flags=re.IGNORECASE)
            clean_name = re.sub(r'\s*\([^)]*\)', '', clean_name)  # Remove parentheses
            clean_name = re.sub(r',.*$', '', clean_name)  # Remove everything after comma
            clean_name = clean_name.strip()

            if len(clean_name) < 2:
                return None

            # Try multiple search strategies
            search_queries = [
                f"{clean_name} band official video",
                f"{clean_name} band music",
                f"{clean_name} official music video",
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
                            return matches[0]

                time.sleep(0.3)

            return None

        except Exception:
            return None

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

            # Try provided format first
            if input_format:
                try:
                    parsed = datetime.strptime(date_str, input_format)
                    if parsed.year == 1900:  # No year in format
                        parsed = parsed.replace(year=current_year)
                        if parsed.date() < today:
                            parsed = parsed.replace(year=current_year + 1)
                    return parsed.strftime("%a, %b %d")
                except ValueError:
                    pass

            # Try common formats
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
                    if parsed.year == 1900:  # No year in format
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

        for i, show in enumerate(shows[:limit], 1):
            # Get YouTube for headliner
            show['youtube_id'] = self.get_youtube_id(show.get('artist'))

            # Get YouTube for opener if exists
            if show.get('opener'):
                show['opener_youtube_id'] = self.get_youtube_id(show['opener'], is_opener=True)

            # Progress output
            print(f"[{i}/{min(len(shows), limit)}] {show.get('artist', 'Unknown')} ({show.get('date', 'TBD')})")
            if show.get('opener'):
                opener_display = show['opener'][:40] + ('...' if len(show.get('opener', '')) > 40 else '')
                print(f"        Opener: {opener_display}")
            if show.get('youtube_id'):
                print(f"        YouTube: {show['youtube_id']}")

            processed.append(show)
            time.sleep(0.5)  # Respectful delay

        return processed
