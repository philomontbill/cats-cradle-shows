#!/usr/bin/env python3
"""
Neighborhood Theatre (Charlotte, NC) Show Scraper with YouTube Integration
Scrapes upcoming shows and finds YouTube videos for each artist.

Uses the same Ticketmaster widget (tw-* CSS classes) as Elevation 27.
"""

import requests
from bs4 import BeautifulSoup
import re
from base_scraper import BaseScraper


class NeighborhoodTheatreScraper(BaseScraper):
    venue_name = "Neighborhood Theatre"
    venue_location = "Charlotte, NC"
    venue_website = "https://neighborhoodtheatre.com"
    output_filename = "data/shows-neighborhood.json"

    def scrape_shows(self):
        """Main scraping function"""
        print("\nFetching events from Neighborhood Theatre...")

        try:
            response = requests.get(
                'https://neighborhoodtheatre.com/calendar/',
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Error fetching page: {e}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all event sections (Ticketmaster widget)
        events = soup.find_all('div', class_='tw-section')

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

        # Sort and save
        shows = self.sort_shows_by_date(shows)
        self.save_json(shows)

        return shows

    def _clean_artist_name(self, title):
        """Extract clean artist name from event title.

        Neighborhood Theatre titles often include tour names after dashes:
        "MAGGIE LINDEMANN – I Feel Everything Tour"
        "Lotus – Rise of the Anglerfish Tour"
        The base class only strips specific keywords after dashes, so we
        use a broader pattern here that catches any "... Tour" suffix.
        """
        if not title or len(title) < 2:
            return None
        # Check event keywords on original name (reuse base class pattern)
        if self.EVENT_KEYWORDS.search(title):
            return None
        if re.match(r'^R\.?I\.?P\.?\s', title):
            return None

        name = title
        # Strip colon + everything after (tour/event info)
        name = re.sub(r':.*$', '', name)
        # Strip any dash followed by text containing "tour", "live", etc.
        tour_patterns = [
            r'\s*[-–—]\s*(.*tour.*|live.*|in concert.*|presents.*)$',
            r'\s*\(.*tour.*\)$',
            r'\s*:\s*.*tour.*$',
        ]
        for pattern in tour_patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)

        # Strip remaining dashes (take first part)
        if ' – ' in name:
            name = name.split(' – ')[0]
        elif ' - ' in name and 'with' not in name.lower():
            name = name.split(' - ')[0]

        # Strip "with" / "w/" to separate opener
        if ' with ' in name.lower():
            name = re.split(r'\s+with\s+', name, flags=re.IGNORECASE)[0]
        if ' w/ ' in name.lower():
            name = re.split(r'\s+w/\s+', name, flags=re.IGNORECASE)[0]

        # Strip parentheticals, "feat.", comma-separated artists
        name = re.sub(r'\s*\([^)]*\)', '', name)
        name = re.sub(r'\s+feat[.:]\s+.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+ft[.:]\s+.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r',.*$', '', name)

        name = name.strip()
        return name if len(name) >= 2 else None

    def _process_event(self, event):
        """Process a single event into our format"""
        try:
            # Get artist name
            name_div = event.find('div', class_='tw-name')
            if not name_div:
                name_div = event.find('span', class_='tw-name')
            if not name_div:
                return None

            artist_link = name_div.find('a')
            if not artist_link:
                return None

            full_title = artist_link.get_text(strip=True)
            artist = self._clean_artist_name(full_title)

            if not artist:
                return None

            # Get date
            date_span = event.find('span', class_='tw-event-date')
            date = ''
            if date_span:
                date_text = date_span.get_text(strip=True)
                date = self.format_date_standard(date_text)

            # Get image
            img = event.find('img', class_='event-img')
            if not img:
                img = event.find('img')
            image = img.get('src') if img else None

            # Get doors time
            doors_span = event.find('span', class_='tw-event-door-time')
            doors = doors_span.get_text(strip=True) if doors_span else None
            if doors:
                doors = self._format_time(doors)

            # Get show time
            time_span = event.find('span', class_='tw-event-time')
            showtime = None
            if time_span:
                time_text = time_span.get_text(strip=True)
                if 'Show:' in time_text:
                    showtime = time_text.replace('Show:', '').strip()
                else:
                    showtime = time_text
                showtime = self._format_time(showtime)

            # Get ticket URL
            ticket_link = event.find('a', class_='tw-buy-tix-btn')
            ticket_url = ticket_link.get('href') if ticket_link else None

            # Check if sold out
            notice = None
            if ticket_link:
                link_classes = ticket_link.get('class', [])
                if 'tw_soldout' in link_classes:
                    notice = "Sold Out"
                elif 'Sold Out' in ticket_link.get_text():
                    notice = "Sold Out"

            # Get age restriction
            age_div = event.find('div', class_='tw-age-restriction')
            age_text = age_div.get_text(strip=True) if age_div else None
            if age_text and '18' in age_text and not notice:
                notice = "18+"

            # Try to extract opener from title
            opener = self._extract_opener(full_title)

            return {
                'artist': artist,
                'date': date,
                'venue': 'Neighborhood Theatre',
                'opener': opener,
                'notice': notice,
                'doors': doors,
                'showtime': showtime,
                'image': image,
                'ticket_url': ticket_url
            }

        except Exception:
            return None

    def _extract_opener(self, title):
        """Extract opener from event title if present"""
        patterns = [
            r'\s+with\s+(.+?)(?:\s*[-–—]|$)',
            r'\s+w/\s+(.+?)(?:\s*[-–—]|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                opener = match.group(1).strip()
                opener = re.sub(r'\s*[-–—].*$', '', opener)
                return opener

        return None

    def _format_time(self, time_str):
        """Format time to lowercase: 7:00PM -> 7 pm"""
        if not time_str:
            return None
        time_str = time_str.replace(':00', '').lower()
        time_str = time_str.replace('pm', ' pm').replace('am', ' am')
        return time_str.strip()


def main():
    scraper = NeighborhoodTheatreScraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! Neighborhood Theatre shows ready.")
    else:
        print("\nNo shows found. Check your connection and try again.")


if __name__ == "__main__":
    main()
