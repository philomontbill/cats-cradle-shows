#!/usr/bin/env python3
"""
Kings Raleigh Scraper
Scrapes upcoming shows from kingsraleigh.com (Raleigh, NC)
"""

import requests
from bs4 import BeautifulSoup
import re
import html
from base_scraper import BaseScraper


class KingsScraper(BaseScraper):
    venue_name = "Kings"
    venue_location = "Raleigh, NC"
    venue_website = "https://kingsraleigh.com"
    output_filename = "data/shows-kings.json"

    def scrape_shows(self):
        """Main scraping function"""
        print("\nFetching events from Kings...")

        shows = self._fetch_events()

        if not shows:
            print("No events found")
            return []

        print(f"Found {len(shows)} events\n")

        # Add YouTube videos
        shows = self.process_shows_with_youtube(shows)

        # Sort by date
        shows = self.sort_shows_by_date(shows)

        # Save to JSON
        self.save_json(shows)

        return shows

    def _fetch_events(self):
        """Fetch and parse events from the events page"""
        try:
            response = requests.get(
                'https://kingsraleigh.com/events/',
                headers=self.headers,
                timeout=15,
                allow_redirects=True
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            shows = []
            seen_artists = set()

            # Find event rows in the table
            rows = soup.find_all('tr')

            for row in rows:
                # Look for rows with date paragraph
                date_p = row.find('p', class_='date')
                if not date_p:
                    continue

                show = self._parse_event_row(row, date_p)
                if show and show.get('artist'):
                    # Deduplicate
                    key = f"{show['artist']}-{show['date']}"
                    if key not in seen_artists:
                        seen_artists.add(key)
                        shows.append(show)

            return shows[:30]

        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def _parse_event_row(self, row, date_p):
        """Parse a single event row"""
        try:
            show = {
                'venue': self.venue_name
            }

            # Extract date from p.date
            date_text = date_p.get_text().strip()
            show['date'] = self._parse_date(date_text)

            # Extract artist name from h3
            h3 = row.find('h3')
            if h3:
                # Get text without the opener (which is in <em>)
                artist = h3.get_text().strip()
                # Clean up
                artist = html.unescape(artist)
                # Remove presenter prefix if present
                artist = re.sub(r'^[A-Z][A-Za-z\s]+ presents\s*', '', artist)
                # Remove opener portion after "with"
                artist = re.split(r'\s+with\s+', artist, flags=re.IGNORECASE)[0]
                show['artist'] = artist.strip()

            if not show.get('artist'):
                return None

            # Extract opener from h4
            h4 = row.find('h4', style=lambda x: x and '#0a6770' in x)
            if h4:
                opener_text = h4.get_text().strip()
                opener_text = html.unescape(opener_text)
                # Remove "with " prefix
                opener_text = re.sub(r'^with\s+', '', opener_text, flags=re.IGNORECASE)
                if opener_text and len(opener_text) > 2:
                    show['opener'] = opener_text

            # Extract time
            time_p = row.find('p', string=re.compile(r'Time:', re.IGNORECASE))
            if time_p:
                time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', time_p.get_text(), re.IGNORECASE)
                if time_match:
                    show['showtime'] = time_match.group(1).lower()
            else:
                # Try finding time in any p tag
                for p in row.find_all('p'):
                    time_match = re.search(r'Time:\s*(\d{1,2}:\d{2}\s*[AP]M)', p.get_text(), re.IGNORECASE)
                    if time_match:
                        show['showtime'] = time_match.group(1).lower()
                        break

            # Extract ticket URL
            link = row.find('a', href=lambda x: x and '/shows/' in x)
            if link:
                href = link.get('href')
                show['ticket_url'] = href

            # Extract image from background-image or img tag
            img = row.find('img')
            if img:
                src = img.get('src')
                if src:
                    show['image'] = src
            else:
                # Check for background-image in style
                td = row.find('td', style=lambda x: x and 'background-image' in str(x))
                if td:
                    style = td.get('style', '')
                    bg_match = re.search(r'background-image:\s*url\(([^)]+)\)', style)
                    if bg_match:
                        show['image'] = bg_match.group(1).strip('"\'')

            show['notice'] = None
            show['doors'] = None

            return show

        except Exception as e:
            return None

    def _parse_date(self, date_str):
        """Parse date string like 'Thursday, February 5th, 2026'"""
        try:
            # Remove ordinal suffixes
            clean = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
            # Extract components
            match = re.search(r'(\w+),?\s+(\w+)\s+(\d{1,2})', clean)
            if match:
                day_name = match.group(1)[:3]
                month = match.group(2)[:3]
                day = match.group(3)
                return f"{day_name}, {month} {day}"
        except:
            pass
        return 'TBD'


def main():
    scraper = KingsScraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! Kings shows ready.")
    else:
        print("\nNo shows found. Check connection and try again.")


if __name__ == "__main__":
    main()
