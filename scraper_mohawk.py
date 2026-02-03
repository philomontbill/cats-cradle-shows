#!/usr/bin/env python3
"""
Mohawk Austin Show Scraper with YouTube Integration
Fetches shows from Prekindle API and finds YouTube videos for each artist
"""

import requests
import json
import time
from base_scraper import BaseScraper


class MohawkScraper(BaseScraper):
    venue_name = "Mohawk"
    venue_location = "Austin, TX"
    venue_website = "https://www.mohawkaustin.com"
    output_filename = "shows-mohawk.json"

    def __init__(self):
        super().__init__()
        self.api_url = "https://www.prekindle.com/api/events/organizer/531433527670566235"

    def scrape_shows(self):
        """Main scraping function"""
        print("\nFetching events from Prekindle API...")
        events = self._fetch_events()

        if not events:
            print("No events found")
            return []

        print(f"Found {len(events)} events\n")

        # Process events into our format
        shows = []
        for event in events[:25]:
            show = self._process_event(event)
            if show:
                shows.append(show)

        # Add YouTube videos with progress output
        shows = self.process_shows_with_youtube(shows)

        # Save to JSON
        self.save_json(shows)

        return shows

    def _fetch_events(self):
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

    def _process_event(self, event):
        """Process a single event into our format"""
        try:
            headliner = event.get('headliner') or event.get('title')
            if not headliner:
                return None

            # Parse support acts
            support = event.get('support')
            opener = support if support and support.lower() != 'none' else None

            # Format date
            date_str = event.get('date', '')
            date = self.format_date_standard(date_str, "%m/%d/%Y")

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

            # Check for sold out or other status
            notice = None
            availability = event.get('availability', '').upper()
            if availability == 'SOLD_OUT':
                notice = "Sold Out"
            elif availability == 'CANCELLED':
                notice = "Cancelled"
            elif availability == 'POSTPONED':
                notice = "Postponed"

            return {
                'artist': headliner,
                'date': date,
                'venue': venue,
                'opener': opener,
                'notice': notice,
                'doors': doors,
                'showtime': showtime,
                'image': image,
                'ticket_url': ticket_url
            }

        except Exception:
            return None


def main():
    scraper = MohawkScraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! Mohawk shows ready.")
    else:
        print("\nNo shows found. Check your connection and try again.")


if __name__ == "__main__":
    main()
