#!/usr/bin/env python3
"""
Local 506 Scraper
Scrapes upcoming shows from local506.com (Chapel Hill, NC)
"""

import requests
from bs4 import BeautifulSoup
import re
import html
from base_scraper import BaseScraper


class Local506Scraper(BaseScraper):
    venue_name = "Local 506"
    venue_location = "Chapel Hill, NC"
    venue_website = "https://local506.com"
    output_filename = "shows-local506.json"

    def scrape_shows(self):
        """Main scraping function"""
        print("\nFetching events from Local 506...")

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

    def _clean_html_entities(self, text):
        """Clean up HTML entities in text"""
        if not text:
            return text
        text = html.unescape(text)
        return text

    def _fetch_events(self):
        """Fetch and parse events from the main page"""
        try:
            # Local 506 shows events on main page
            response = requests.get(
                'https://local506.com/',
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            shows = []

            # Find event containers
            event_containers = soup.find_all('div', class_='rhpSingleEvent')
            if not event_containers:
                event_containers = soup.find_all('div', class_='eventWrapper')

            for container in event_containers[:30]:
                show = self._parse_event(container)
                if show and show.get('artist'):
                    shows.append(show)

            return shows

        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def _parse_event(self, container):
        """Parse a single event container"""
        try:
            show = {
                'venue': self.venue_name
            }

            # Extract artist name from title link
            title_link = container.find('a', class_='url')
            if title_link:
                show['artist'] = title_link.get('title', '').strip()
                if not show['artist']:
                    h2 = container.find('h2')
                    if h2:
                        show['artist'] = h2.get_text().strip()

            if not show.get('artist'):
                return None

            # Clean up HTML entities
            show['artist'] = self._clean_html_entities(show['artist'])

            # Extract date from eventDate div
            date_elem = container.find(id='eventDate')
            if not date_elem:
                date_elem = container.find(class_='eventMonth')
            if not date_elem:
                date_elem = container.find(class_='singleEventDate')

            if date_elem:
                date_text = date_elem.get_text().strip()
                match = re.search(r'(\w{3}),?\s+(\w{3})\s+(\d{1,2})', date_text)
                if match:
                    show['date'] = f"{match.group(1)}, {match.group(2)} {match.group(3)}"
                else:
                    show['date'] = 'TBD'
            else:
                show['date'] = 'TBD'

            # Extract times
            container_text = container.get_text()

            doors_match = re.search(r'Doors?:?\s*(\d{1,2}(?::\d{2})?\s*[ap]m)', container_text, re.IGNORECASE)
            if doors_match:
                show['doors'] = doors_match.group(1).lower()

            show_match = re.search(r'Show:?\s*(\d{1,2}(?::\d{2})?\s*[ap]m)', container_text, re.IGNORECASE)
            if show_match:
                show['showtime'] = show_match.group(1).lower()

            # Extract opener from subheader
            subheader = container.find(class_='eventSubHeader')
            if subheader:
                opener_text = subheader.get_text().strip()
                opener_text = self._clean_html_entities(opener_text)
                if opener_text and len(opener_text) > 2 and len(opener_text) < 150:
                    show['opener'] = opener_text

            # Check for "with" or "w/" pattern in title
            if not show.get('opener'):
                artist = show.get('artist', '')
                w_match = re.search(r'\s+[wW]/\s+(.+)$', artist)
                if not w_match:
                    w_match = re.search(r'\s+with\s+(.+)$', artist, re.IGNORECASE)
                if w_match:
                    show['opener'] = w_match.group(1).strip()
                    show['artist'] = artist[:w_match.start()].strip()

            # Extract image
            img = container.find('img')
            if img:
                src = img.get('src') or img.get('data-src')
                if src:
                    if src.startswith('/'):
                        src = f"https://local506.com{src}"
                    show['image'] = src

            # Extract ticket URL (ETIX)
            ticket_link = container.find('a', href=lambda x: x and 'etix.com' in x)
            if ticket_link:
                show['ticket_url'] = ticket_link.get('href')
            else:
                event_link = container.find('a', class_='url')
                if event_link:
                    href = event_link.get('href')
                    if href:
                        show['ticket_url'] = href

            # Check for notices
            show['notice'] = None
            text_lower = container_text.lower()
            if 'sold out' in text_lower:
                show['notice'] = 'Sold Out'
            elif 'cancelled' in text_lower or 'canceled' in text_lower:
                show['notice'] = 'Cancelled'
            elif 'postponed' in text_lower:
                show['notice'] = 'Postponed'

            return show

        except Exception as e:
            return None


def main():
    scraper = Local506Scraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! Local 506 shows ready.")
    else:
        print("\nNo shows found. Check connection and try again.")


if __name__ == "__main__":
    main()
