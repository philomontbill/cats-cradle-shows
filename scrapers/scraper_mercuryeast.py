#!/usr/bin/env python3
"""
Mercury East Venues Scraper (Bowery Ballroom & Mercury Lounge)
Scrapes from mercuryeastpresents.com and outputs separate JSON files per venue
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import json
from datetime import datetime
from base_scraper import BaseScraper


class MercuryEastScraper(BaseScraper):
    """Scraper for Mercury East venues - outputs files for each venue."""

    venue_name = "Mercury East"  # Parent company
    venue_location = "New York, NY"
    venue_website = "https://mercuryeastpresents.com"
    output_filename = "data/shows-mercuryeast.json"  # Not used directly

    # Venue configurations
    VENUES = {
        'boweryballroom': {
            'name': 'Bowery Ballroom',
            'location': 'New York, NY',
            'website': 'https://www.boweryballroom.com',
            'output': 'data/shows-boweryballroom.json',
            'venue_page': '/tm-venue/bowery-ballroom/'
        },
        'mercurylounge': {
            'name': 'Mercury Lounge',
            'location': 'New York, NY',
            'website': 'https://www.mercuryloungenyc.com',
            'output': 'data/shows-mercurylounge.json',
            'venue_page': '/tm-venue/mercury-lounge/'
        }
    }

    def __init__(self):
        super().__init__()
        self.base_url = "http://www.mercuryeastpresents.com"
        self.all_events = []

    def scrape_shows(self):
        """Main scraping function - scrapes both venues."""
        print("\nFetching events from Mercury East...")

        # Get all events from the main page
        self.all_events = self._fetch_all_events()

        if not self.all_events:
            print("No events found")
            return []

        print(f"Found {len(self.all_events)} total events\n")

        # Process each venue
        for venue_key, venue_config in self.VENUES.items():
            print(f"\n{'='*40}")
            print(f"Processing {venue_config['name']}...")
            print(f"{'='*40}")

            self._process_venue(venue_key, venue_config)

        return self.all_events

    def _fetch_all_events(self):
        """Fetch events from venue-specific pages (/tm-venue/) for reliable separation.

        Uses structured HTML (tw-details-container cards) which include artist,
        date, doors, opener, and venue — no full-text guessing needed.
        """
        events = []

        for venue_key, venue_config in self.VENUES.items():
            url = f"{self.base_url}{venue_config['venue_page']}"
            try:
                response = requests.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"Error fetching {venue_config['name']} events: {e}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            for card in soup.find_all('div', class_='tw-details-container'):
                # Artist name
                name_el = card.find('div', class_='tw-name')
                if not name_el:
                    continue
                link = name_el.find('a', href=re.compile(r'/tm-event/'))
                if not link:
                    continue

                artist = link.get_text(strip=True)
                event_url = link.get('href', '')
                if not artist or not event_url:
                    continue

                # Clean SOLD OUT prefix
                artist = artist.replace('&amp;', '&')
                artist = re.sub(r'^\*?SOLD OUT\*?\s*', '', artist, flags=re.IGNORECASE)

                # Date (e.g. "Tue Mar 10, 2026")
                date_el = card.find('span', class_='tw-event-date')
                date_raw = date_el.get_text(strip=True) if date_el else ''

                # Doors (e.g. "Doors: 7:00 pm")
                time_el = card.find('span', class_='tw-event-time')
                doors = None
                if time_el:
                    time_text = time_el.get_text(strip=True)
                    doors_match = re.search(r'(\d{1,2}(?::\d{2})?\s*[ap]m)', time_text, re.IGNORECASE)
                    if doors_match:
                        doors = doors_match.group(1).lower()

                # Opener (e.g. "with Niall Connolly")
                opener_el = card.find('div', class_='tw-attractions')
                opener = None
                if opener_el:
                    opener_text = opener_el.get_text(strip=True)
                    with_match = re.match(r'with\s*(.+)', opener_text, re.IGNORECASE)
                    if with_match:
                        opener = with_match.group(1).strip()

                # Sold out
                notice = None
                if 'sold out' in (name_el.get_text(strip=True)).lower():
                    notice = 'Sold Out'

                # Deduplicate by URL
                if any(e['event_url'] == event_url for e in events):
                    continue

                events.append({
                    'artist': artist,
                    'date_raw': date_raw,
                    'event_url': event_url,
                    'source_venue': venue_key,
                    'doors': doors,
                    'opener': opener,
                    'notice': notice
                })

        return events

    def _process_venue(self, venue_key, venue_config):
        """Process events for a specific venue."""
        shows = []

        # Filter events by source venue tag (set during fetch)
        venue_events = []

        print(f"Checking events for {venue_config['name']}...")

        for event in self.all_events:
            if event.get('source_venue') != venue_key:
                continue
            # Fetch event detail page for image (artist/date/opener already from venue page)
            details = self._fetch_event_details(event['event_url'])
            if details:
                event['image'] = details.get('image')
            venue_events.append(event)

        print(f"Found {len(venue_events)} events at {venue_config['name']}\n")

        if not venue_events:
            return

        # Build show list
        # TODO: /tm-venue/ pages currently return only ~20 events each.
        # Investigate if they paginate — goal is 40+ per venue so each gets 20+ with videos.
        for event in venue_events[:25]:
            show = self._create_show(event, venue_config)
            if show:
                shows.append(show)

        # Add YouTube videos using shared method (rejection filtering, smart search, quota saving)
        shows = self.process_shows_with_youtube(shows)

        # Save to venue-specific JSON
        self._save_venue_json(shows, venue_config)

    def _fetch_event_details(self, url):
        """Fetch details from an individual event page."""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Get og:description for details
            og_desc = soup.find('meta', property='og:description')
            description = og_desc.get('content', '') if og_desc else ''

            # Get og:image
            og_image = soup.find('meta', property='og:image')
            image = og_image.get('content', '') if og_image else None

            # Parse description like:
            # "The Veldt with Blak Emoji, Bird Streets [Ages 21+, Doors Open 6pm, $15 Advance]"
            details = self._parse_description(description)
            details['image'] = image

            return details

        except Exception:
            return None

    def _parse_description(self, description):
        """Parse event description for opener, door time, etc."""
        details = {
            'opener': None,
            'doors': None,
            'notice': None,
            'age': None
        }

        if not description:
            return details

        # Check for "with" to find opener
        with_match = re.search(r'\bwith\s+([^[\]]+?)(?:\s*\[|$)', description, re.IGNORECASE)
        if with_match:
            details['opener'] = with_match.group(1).strip()

        # Check for bracket content [Ages 21+, Doors Open 6pm, ...]
        bracket_match = re.search(r'\[([^\]]+)\]', description)
        if bracket_match:
            bracket_content = bracket_match.group(1)

            # Door time
            doors_match = re.search(r'Doors?\s*(?:Open\s*)?(\d{1,2}(?::\d{2})?\s*[ap]m)', bracket_content, re.IGNORECASE)
            if doors_match:
                details['doors'] = doors_match.group(1).lower()

            # Age restriction
            age_match = re.search(r'Ages?\s*(\d+\+)', bracket_content, re.IGNORECASE)
            if age_match:
                details['age'] = age_match.group(1)

            # Sold out
            if 'sold out' in bracket_content.lower():
                details['notice'] = 'Sold Out'

        # Check for sold out in main text
        if '*SOLD OUT*' in description.upper() or 'SOLD OUT' in description.upper():
            details['notice'] = 'Sold Out'

        return details

    def _create_show(self, event, venue_config):
        """Create a show dict from event data."""
        # Format date — venue page gives "Tue Mar 10, 2026", we want "Tue, Mar 10"
        date = "TBD"
        if event.get('date_raw'):
            try:
                parsed = datetime.strptime(event['date_raw'], "%a %b %d, %Y")
                date = parsed.strftime("%a, %b %d")
            except (ValueError, TypeError):
                date = event['date_raw']

        return {
            'artist': event.get('artist', 'Unknown'),
            'date': date,
            'venue': venue_config['name'],
            'opener': event.get('opener'),
            'notice': event.get('notice'),
            'doors': event.get('doors'),
            'showtime': None,
            'image': event.get('image'),
            'ticket_url': event.get('event_url')
        }

    def _save_venue_json(self, shows, venue_config):
        """Save shows to venue-specific JSON file."""
        data = {
            'venue': {
                'name': venue_config['name'],
                'location': venue_config['location'],
                'website': venue_config['website']
            },
            'shows': shows,
            'total_shows': len(shows),
            'shows_with_video': sum(1 for s in shows if s.get('youtube_id')),
            'shows_with_image': sum(1 for s in shows if s.get('image')),
            'last_updated': datetime.now().isoformat()
        }

        with open(venue_config['output'], 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nSaved {len(shows)} shows to {venue_config['output']}")
        print(f"  - {data['shows_with_video']} have YouTube videos")
        print(f"  - {data['shows_with_image']} have images")


def main():
    scraper = MercuryEastScraper()
    scraper.scrape_shows()
    print("\nDone! Mercury East venues ready.")


if __name__ == "__main__":
    main()
