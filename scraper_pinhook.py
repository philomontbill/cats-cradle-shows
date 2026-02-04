#!/usr/bin/env python3
"""
The Pinhook Scraper
Scrapes upcoming shows from thepinhook.com
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from base_scraper import BaseScraper


class PinhookScraper(BaseScraper):
    venue_name = "The Pinhook"
    venue_location = "Durham, NC"
    venue_website = "https://thepinhook.com"
    output_filename = "shows-pinhook.json"

    def scrape_shows(self):
        """Main scraping function"""
        print("\nFetching events from The Pinhook...")

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
                'https://thepinhook.com/events/',
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            shows = []

            # Find event containers - try multiple selectors
            event_containers = soup.find_all('div', class_='eventWrapper')
            if not event_containers:
                event_containers = soup.find_all('div', class_='rhpSingleEvent')
            if not event_containers:
                # Try finding by event links
                event_links = soup.find_all('a', class_='eventMoreInfo')
                for link in event_links:
                    container = link.find_parent('div', class_=True)
                    if container and container not in event_containers:
                        event_containers.append(container)

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

            # Extract artist name
            title_elem = container.find('h2') or container.find(id='eventTitle')
            if title_elem:
                show['artist'] = title_elem.get_text().strip()
            else:
                # Try finding title link
                title_link = container.find('a', href=lambda x: x and '/event/' in x)
                if title_link:
                    show['artist'] = title_link.get_text().strip()

            if not show.get('artist'):
                return None

            # Extract date - look for eventDate div with eventMonth class
            date_elem = container.find(id='eventDate')
            if not date_elem:
                date_elem = container.find(class_='eventMonth')
            if not date_elem:
                date_elem = container.find(class_='singleEventDate')

            if date_elem:
                date_text = date_elem.get_text().strip()
                # Format is like "Wed, Feb 04"
                match = re.search(r'(\w{3}),?\s+(\w{3})\s+(\d{1,2})', date_text)
                if match:
                    show['date'] = f"{match.group(1)}, {match.group(2)} {match.group(3)}"
                else:
                    # Try other patterns
                    match2 = re.search(r'(\w+)\s+(\d{1,2})', date_text)
                    if match2:
                        show['date'] = self.format_date_standard(f"{match2.group(1)} {match2.group(2)}")

            if not show.get('date'):
                show['date'] = 'TBD'

            # Extract times (doors/show)
            container_text = container.get_text()

            doors_match = re.search(r'Doors?:?\s*(\d{1,2}(?::\d{2})?\s*[ap]m)', container_text, re.IGNORECASE)
            if doors_match:
                show['doors'] = doors_match.group(1).lower()

            show_match = re.search(r'Show:?\s*(\d{1,2}(?::\d{2})?\s*[ap]m)', container_text, re.IGNORECASE)
            if show_match:
                show['showtime'] = show_match.group(1).lower()

            # Extract opener from subheader or "with" pattern
            subheader = container.find(class_='eventSubHeader')
            if subheader:
                opener_text = subheader.get_text().strip()
                # Remove presenter info like "andmoreagain presents"
                opener_text = re.sub(r'.*presents\s*', '', opener_text, flags=re.IGNORECASE)
                if opener_text and len(opener_text) > 2:
                    show['opener'] = opener_text

            # Also check for "with" pattern
            if not show.get('opener'):
                with_match = re.search(r'\bwith\s+([A-Z][^,\n]+?)(?:\s*,|\s*\n|\s*Doors|\s*Show|\s*$)', container_text)
                if with_match:
                    opener = with_match.group(1).strip()
                    if len(opener) > 2 and len(opener) < 100:
                        show['opener'] = opener

            # Extract image
            img = container.find('img')
            if img:
                src = img.get('src') or img.get('data-src')
                if src:
                    if src.startswith('/'):
                        src = f"https://thepinhook.com{src}"
                    show['image'] = src

            # Extract ticket URL (ETIX)
            ticket_link = container.find('a', href=lambda x: x and 'etix.com' in x)
            if ticket_link:
                show['ticket_url'] = ticket_link.get('href')
            else:
                # Try "More Info" link as fallback
                more_info = container.find('a', class_='eventMoreInfo')
                if more_info:
                    href = more_info.get('href')
                    if href:
                        if href.startswith('/'):
                            href = f"https://thepinhook.com{href}"
                        show['ticket_url'] = href

            # Check for notices (sold out, etc)
            show['notice'] = None
            if 'sold out' in container_text.lower():
                show['notice'] = 'Sold Out'
            elif 'cancelled' in container_text.lower() or 'canceled' in container_text.lower():
                show['notice'] = 'Cancelled'
            elif 'postponed' in container_text.lower():
                show['notice'] = 'Postponed'

            return show

        except Exception as e:
            return None


def main():
    scraper = PinhookScraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! The Pinhook shows ready.")
    else:
        print("\nNo shows found. Check connection and try again.")


if __name__ == "__main__":
    main()
