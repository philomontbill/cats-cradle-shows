#!/usr/bin/env python3
"""
Elevation 27 Show Scraper with YouTube Integration
Scrapes upcoming shows and finds YouTube videos for each artist
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from base_scraper import BaseScraper


class Elevation27Scraper(BaseScraper):
    venue_name = "Elevation 27"
    venue_location = "Virginia Beach, VA"
    venue_website = "https://www.elevation27.com"
    output_filename = "shows-elevation27.json"

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

    def _process_event(self, event):
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
            artist = self._clean_artist_name(full_title)

            if not artist:
                return None

            # Get date
            date_span = event.find('span', class_='tw-event-date')
            date = date_span.get_text(strip=True) if date_span else ''
            date = self._format_date(date)

            # Get image
            img = event.find('img', class_='event-img')
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
                if 'tw_soldout' in ticket_link.get('class', []):
                    notice = "Sold Out"
                elif 'Sold Out' in ticket_link.get_text():
                    notice = "Sold Out"

            # Get age restriction as notice if notable
            age_div = event.find('div', class_='tw-age-restriction')
            age_text = age_div.get_text(strip=True) if age_div else None
            if age_text and '18' in age_text and not notice:
                notice = "18+"

            # Try to extract opener from title
            opener = self._extract_opener(full_title)

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

        except Exception:
            return None

    def _clean_artist_name(self, title):
        """Extract clean artist name from event title"""
        patterns = [
            r'\s*[-–—]\s*(.*tour.*|live.*|in concert.*|presents.*)$',
            r'\s*\(.*tour.*\)$',
            r'\s*:\s*.*tour.*$',
        ]

        name = title
        for pattern in patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)

        if ' – ' in name:
            name = name.split(' – ')[0]
        elif ' - ' in name and 'with' not in name.lower():
            name = name.split(' - ')[0]

        if ' with ' in name.lower():
            name = re.split(r'\s+with\s+', name, flags=re.IGNORECASE)[0]
        if ' w/ ' in name.lower():
            name = re.split(r'\s+w/\s+', name, flags=re.IGNORECASE)[0]

        return name.strip()

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

    def _format_date(self, date_str):
        """Format date to match other venues: 'Sat, Feb 07'"""
        # Input format: "Feb Sat 07"
        parts = date_str.split()
        if len(parts) >= 3:
            month = parts[0]
            day_name = parts[1]
            day_num = parts[2]
            return f"{day_name}, {month} {day_num}"
        return date_str

    def _format_time(self, time_str):
        """Format time to lowercase: 7:00PM -> 7 pm"""
        if not time_str:
            return None
        time_str = time_str.replace(':00', '').lower()
        time_str = time_str.replace('pm', ' pm').replace('am', ' am')
        return time_str.strip()


def main():
    scraper = Elevation27Scraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! Elevation 27 shows ready.")
    else:
        print("\nNo shows found. Check your connection and try again.")


if __name__ == "__main__":
    main()
