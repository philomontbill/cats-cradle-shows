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
            'filter': 'bowery'
        },
        'mercurylounge': {
            'name': 'Mercury Lounge',
            'location': 'New York, NY',
            'website': 'https://www.mercuryloungenyc.com',
            'output': 'data/shows-mercurylounge.json',
            'filter': 'mercury lounge'
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
        """Fetch and parse all events from the main page."""
        try:
            # Fetch both venue pages to get all events
            events = []

            for venue_key in self.VENUES.keys():
                url = f"{self.base_url}/{venue_key}"
                response = requests.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()

                # Parse EventData.events.push() calls from JavaScript
                # Pattern handles nested braces in the data object
                pattern = r'EventData\.events\.push\(\{"value"\s*:\s*"([^"]+)"[^}]+?"url"\s*:\s*"([^"]+)"'
                matches = re.findall(pattern, response.text)

                for value, url in matches:
                    event = self._parse_event_data(value, url)
                    if event and event not in events:
                        events.append(event)

            return events

        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def _parse_event_data(self, value, url):
        """Parse event data from value and url."""
        try:
            # Parse artist and date from value like "The Veldt 02/03"
            date_match = re.search(r'\s+(\d{2}/\d{2})$', value)
            if date_match:
                date_str = date_match.group(1)
                artist = value[:date_match.start()].strip()
            else:
                date_str = ""
                artist = value.strip()

            # Clean up HTML entities
            artist = artist.replace('&amp;', '&')

            # Skip if artist contains "SOLD OUT" prefix - we'll get this from the page
            artist = re.sub(r'^\*?SOLD OUT\*?\s*', '', artist, flags=re.IGNORECASE)

            return {
                'artist': artist,
                'date_raw': date_str,
                'event_url': url
            }

        except Exception:
            return None

    def _process_venue(self, venue_key, venue_config):
        """Process events for a specific venue."""
        shows = []

        # Filter events by fetching each event page and checking venue
        venue_events = []

        print(f"Checking events for {venue_config['name']}...")

        for event in self.all_events:
            # Fetch event page to get venue and details
            details = self._fetch_event_details(event['event_url'])

            if details and venue_config['filter'].lower() in details.get('venue', '').lower():
                event.update(details)
                venue_events.append(event)

        print(f"Found {len(venue_events)} events at {venue_config['name']}\n")

        if not venue_events:
            return

        # Build show list
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

            # Try to determine venue from page content
            page_text = soup.get_text().lower()
            if 'bowery ballroom' in page_text:
                details['venue'] = 'Bowery Ballroom'
            elif 'mercury lounge' in page_text:
                details['venue'] = 'Mercury Lounge'
            else:
                # Check URL or other indicators
                if 'bowery' in url.lower():
                    details['venue'] = 'Bowery Ballroom'
                else:
                    details['venue'] = 'Mercury Lounge'

            return details

        except Exception as e:
            return {'venue': ''}

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
        # Format date
        date = "TBD"
        if event.get('date_raw'):
            try:
                # Parse MM/DD format
                current_year = datetime.now().year
                parsed = datetime.strptime(f"{event['date_raw']}/{current_year}", "%m/%d/%Y")

                # If date is in the past, assume next year
                if parsed.date() < datetime.now().date():
                    parsed = parsed.replace(year=current_year + 1)

                date = parsed.strftime("%a, %b %d")
            except:
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
