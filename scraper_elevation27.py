#!/usr/bin/env python3
"""
Elevation 27 Show Scraper with YouTube Integration
Scrapes upcoming shows and finds YouTube videos for each artist
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime
from urllib.parse import quote_plus


class Elevation27Scraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.overrides = self.load_overrides()
        print("Elevation 27 Show Scraper")
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
        print("\nFetching events from Elevation 27...")

        try:
            response = requests.get(
                'https://www.elevation27.com/',
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Error fetching page: {e}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all event sections
        events = soup.find_all('div', class_='tw-section')

        if not events:
            print("No events found")
            return []

        print(f"Found {len(events)} events\n")

        shows = []
        for i, event in enumerate(events[:25], 1):  # Limit to 25 shows
            show = self.process_event(event)
            if show:
                # Search YouTube for the artist
                artist_overrides = self.overrides.get('artist_youtube', {})
                if show['artist'] in artist_overrides:
                    video_id = artist_overrides[show['artist']]
                else:
                    video_id = self.search_youtube(show['artist'])
                show['youtube_id'] = video_id

                # Search YouTube for opener if there is one
                if show.get('opener'):
                    opener_overrides = self.overrides.get('opener_youtube', {})
                    first_opener = show['opener'].split(',')[0].strip()
                    if first_opener in opener_overrides:
                        opener_video_id = opener_overrides[first_opener]
                    else:
                        opener_video_id = self.search_youtube(first_opener)
                    show['opener_youtube_id'] = opener_video_id

                print(f"[{i}/25] {show['artist']} ({show['date']})")
                if show.get('opener'):
                    print(f"        Opener: {show['opener'][:40]}{'...' if len(show.get('opener','')) > 40 else ''}")
                if video_id:
                    print(f"        YouTube: {video_id}")

                shows.append(show)

            time.sleep(0.5)  # Brief delay for YouTube searches

        # Save to JSON
        self.save_json(shows)

        return shows

    def process_event(self, event):
        """Process a single event into our format"""
        try:
            # Get artist name
            name_div = event.find('div', class_='tw-name')
            if not name_div:
                return None

            artist_link = name_div.find('a')
            if not artist_link:
                return None

            full_title = artist_link.get_text(strip=True)
            # Clean up artist name - remove tour names, etc.
            artist = self.clean_artist_name(full_title)

            if not artist:
                return None

            # Get date
            date_span = event.find('span', class_='tw-event-date')
            date = date_span.get_text(strip=True) if date_span else ''
            date = self.format_date(date)

            # Get image
            img = event.find('img', class_='event-img')
            image = img.get('src') if img else None

            # Get doors time
            doors_span = event.find('span', class_='tw-event-door-time')
            doors = doors_span.get_text(strip=True) if doors_span else None
            if doors:
                doors = self.format_time(doors)

            # Get show time
            time_span = event.find('span', class_='tw-event-time')
            showtime = None
            if time_span:
                time_text = time_span.get_text(strip=True)
                if 'Show:' in time_text:
                    showtime = time_text.replace('Show:', '').strip()
                else:
                    showtime = time_text
                showtime = self.format_time(showtime)

            # Get ticket URL
            ticket_link = event.find('a', class_='tw-buy-tix-btn')
            ticket_url = ticket_link.get('href') if ticket_link else None

            # Check if sold out
            notice = None
            if ticket_link:
                if 'tw_soldout' in ticket_link.get('class', []):
                    notice = "Sold Out"
                elif 'Sold Out' in ticket_link.get_text():
                    notice = "Sold Out"

            # Get age restriction as notice if notable
            age_div = event.find('div', class_='tw-age-restriction')
            age_text = age_div.get_text(strip=True) if age_div else None
            if age_text and '18' in age_text and not notice:
                notice = "18+"

            # Try to extract opener from title (often after "with" or "w/")
            opener = self.extract_opener(full_title)

            return {
                'artist': artist,
                'date': date,
                'venue': 'Elevation 27',
                'opener': opener,
                'notice': notice,
                'doors': doors,
                'showtime': showtime,
                'image': image,
                'ticket_url': ticket_url
            }

        except Exception as e:
            return None

    def clean_artist_name(self, title):
        """Extract clean artist name from event title"""
        # Remove common tour/event suffixes
        patterns = [
            r'\s*[-–—]\s*(.*tour.*|live.*|in concert.*|presents.*)$',
            r'\s*\(.*tour.*\)$',
            r'\s*:\s*.*tour.*$',
        ]

        name = title
        for pattern in patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)

        # If there's a " - " or " – ", take the first part as artist
        if ' – ' in name:
            name = name.split(' – ')[0]
        elif ' - ' in name and 'with' not in name.lower():
            name = name.split(' - ')[0]

        # Handle "with" for openers - take part before "with"
        if ' with ' in name.lower():
            name = re.split(r'\s+with\s+', name, flags=re.IGNORECASE)[0]
        if ' w/ ' in name.lower():
            name = re.split(r'\s+w/\s+', name, flags=re.IGNORECASE)[0]

        return name.strip()

    def extract_opener(self, title):
        """Extract opener from event title if present"""
        # Look for "with" or "w/" patterns
        patterns = [
            r'\s+with\s+(.+?)(?:\s*[-–—]|$)',
            r'\s+w/\s+(.+?)(?:\s*[-–—]|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                opener = match.group(1).strip()
                # Clean up the opener name
                opener = re.sub(r'\s*[-–—].*$', '', opener)
                return opener

        return None

    def format_date(self, date_str):
        """Format date to match other venues: 'Sat, Feb 07'"""
        # Input format: "Feb Sat 07"
        parts = date_str.split()
        if len(parts) >= 3:
            month = parts[0]
            day_name = parts[1]
            day_num = parts[2]
            return f"{day_name}, {month} {day_num}"
        return date_str

    def format_time(self, time_str):
        """Format time to lowercase: 7:00PM -> 7 pm"""
        if not time_str:
            return None
        # Convert "7:00PM" to "7 pm"
        time_str = time_str.replace(':00', '').lower()
        time_str = time_str.replace('pm', ' pm').replace('am', ' am')
        return time_str.strip()

    def search_youtube(self, artist_name):
        """Search YouTube for artist's music"""
        try:
            if not artist_name or len(artist_name) < 2:
                return None

            # Clean up artist name
            clean_name = re.sub(r'\s*\([^)]*\)', '', artist_name)
            clean_name = clean_name.strip()

            if len(clean_name) < 2:
                return None

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
                'name': 'Elevation 27',
                'location': 'Virginia Beach, VA',
                'website': 'https://www.elevation27.com'
            },
            'shows': shows,
            'total_shows': len(shows),
            'shows_with_video': sum(1 for s in shows if s.get('youtube_id')),
            'shows_with_image': sum(1 for s in shows if s.get('image')),
            'last_updated': datetime.now().isoformat()
        }

        with open('shows-elevation27.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nSaved {len(shows)} shows to shows-elevation27.json")
        print(f"  - {data['shows_with_video']} have YouTube videos")
        print(f"  - {data['shows_with_image']} have images")


def main():
    scraper = Elevation27Scraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! Elevation 27 shows ready.")
    else:
        print("\nNo shows found. Check your connection and try again.")


if __name__ == "__main__":
    main()
