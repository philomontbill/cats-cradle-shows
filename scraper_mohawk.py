#!/usr/bin/env python3
"""
Mohawk Austin Show Scraper with YouTube Integration
Fetches shows from Prekindle API and finds YouTube videos for each artist
"""

import requests
import json
import re
import time
from datetime import datetime
from urllib.parse import quote_plus


class MohawkScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.api_url = "https://www.prekindle.com/api/events/organizer/531433527670566235"
        self.overrides = self.load_overrides()
        print("Mohawk Austin Show Scraper")
        print("=" * 40)

    def load_overrides(self):
        """Load manual YouTube overrides from overrides.json"""
        try:
            with open('overrides.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"artist_youtube": {}, "opener_youtube": {}}

    def scrape_shows(self):
        """Main scraping function"""
        print("\nFetching events from Prekindle API...")
        events = self.fetch_events()

        if not events:
            print("No events found")
            return []

        print(f"Found {len(events)} events\n")

        shows = []
        for i, event in enumerate(events[:25], 1):  # Limit to 25 shows
            show = self.process_event(event)
            if show:
                # Search YouTube for the headliner
                artist_overrides = self.overrides.get('artist_youtube', {})
                if show['artist'] in artist_overrides:
                    video_id = artist_overrides[show['artist']]
                else:
                    video_id = self.search_youtube(show['artist'])
                show['youtube_id'] = video_id

                # Search YouTube for opener if there is one
                if show.get('opener'):
                    opener_overrides = self.overrides.get('opener_youtube', {})
                    # Get first opener for YouTube search
                    first_opener = show['opener'].split(',')[0].strip()
                    if first_opener in opener_overrides:
                        opener_video_id = opener_overrides[first_opener]
                    else:
                        opener_video_id = self.search_youtube(first_opener)
                    show['opener_youtube_id'] = opener_video_id

                print(f"[{i}/25] {show['artist']} ({show['date']})")
                if show.get('opener'):
                    opener_yt = show.get('opener_youtube_id')
                    print(f"        Opener: {show['opener'][:40]}{'...' if len(show.get('opener','')) > 40 else ''}")
                if video_id:
                    print(f"        YouTube: {video_id}")

                shows.append(show)

            time.sleep(0.5)  # Brief delay for YouTube searches

        # Save to JSON
        self.save_json(shows)

        return shows

    def fetch_events(self):
        """Fetch events from Prekindle API"""
        try:
            response = requests.get(self.api_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            # Remove JSONP callback wrapper
            text = response.text
            if text.startswith('callback('):
                text = text[9:-1]

            data = json.loads(text)
            return data.get('events', [])

        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def process_event(self, event):
        """Process a single event into our format"""
        try:
            headliner = event.get('headliner') or event.get('title')
            if not headliner:
                return None

            # Parse support acts
            support = event.get('support')
            if support and support.lower() != 'none':
                opener = support
            else:
                opener = None

            # Format date
            date_str = event.get('date', '')
            date = self.format_date(date_str, event.get('dayOfWeek'))

            # Get times
            doors = event.get('doorsTime')
            showtime = event.get('time')

            # Get venue (Indoor/Outdoor)
            venue = event.get('venue', 'Mohawk')

            # Get image
            image = event.get('imageUrl')

            # Get ticket URL
            ticket_url = event.get('thirdPartyLink')
            if not ticket_url:
                dtf_links = event.get('dtfLinks', [])
                ticket_url = dtf_links[0] if dtf_links else None

            return {
                'artist': headliner,
                'date': date,
                'venue': venue,
                'opener': opener,
                'doors': doors,
                'showtime': showtime,
                'image': image,
                'ticket_url': ticket_url
            }

        except Exception as e:
            return None

    def format_date(self, date_str, day_of_week=None):
        """Format date to match Cat's Cradle format: 'Fri, Jan 30'"""
        try:
            # Parse MM/DD/YYYY format
            parsed = datetime.strptime(date_str, "%m/%d/%Y")
            return parsed.strftime("%a, %b %d")
        except:
            if day_of_week:
                return f"{day_of_week[:3]}, {date_str}"
            return date_str

    def search_youtube(self, artist_name):
        """Search YouTube for artist's music"""
        try:
            if not artist_name or len(artist_name) < 2:
                return None

            # Clean up artist name
            clean_name = re.sub(r'\s*\([^)]*\)', '', artist_name)  # Remove parentheses
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
        """Save shows to JSON file"""
        data = {
            'venue': {
                'name': 'Mohawk',
                'location': 'Austin, TX',
                'website': 'https://www.mohawkaustin.com'
            },
            'shows': shows,
            'total_shows': len(shows),
            'shows_with_video': sum(1 for s in shows if s.get('youtube_id')),
            'shows_with_image': sum(1 for s in shows if s.get('image')),
            'last_updated': datetime.now().isoformat()
        }

        with open('shows-mohawk.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nSaved {len(shows)} shows to shows-mohawk.json")
        print(f"  - {data['shows_with_video']} have YouTube videos")
        print(f"  - {data['shows_with_image']} have images")


def main():
    scraper = MohawkScraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! Mohawk shows ready.")
    else:
        print("\nNo shows found. Check your connection and try again.")


if __name__ == "__main__":
    main()
