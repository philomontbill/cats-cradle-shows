#!/usr/bin/env python3
"""
The Orange Peel (Asheville, NC) Show Scraper with YouTube Integration
Scrapes upcoming shows and finds YouTube videos for each artist.

Uses the same RHP/eventWrapper pattern as Lincoln Theatre and The Pinhook,
with Orange Peel-specific selectors (gridLayout containers, separate
eventMonth/eventDay spans, h4 openers, ETIX tickets).
"""

import requests
from bs4 import BeautifulSoup
import html
import re
from base_scraper import BaseScraper


class OrangePeelScraper(BaseScraper):
    venue_name = "The Orange Peel"
    venue_location = "Asheville, NC"
    venue_website = "https://theorangepeel.net"
    output_filename = "data/shows-orangepeel.json"

    def scrape_shows(self):
        """Main scraping function"""
        print("\nFetching events from The Orange Peel...")

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
                'https://theorangepeel.net/events/',
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            shows = []

            # Find event containers — Orange Peel uses gridLayout and eventWrapper
            event_containers = soup.find_all('div', class_='gridLayout')
            if not event_containers:
                event_containers = soup.find_all('div', class_='eventWrapper')
            if not event_containers:
                event_containers = soup.find_all('div', class_='rhpSingleEvent')

            for container in event_containers[:25]:
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

            # Extract artist name from eventTitle h2 > a, or fallback to h2 text
            title_div = container.find(id='eventTitle')
            if title_div:
                link = title_div.find('a')
                if link:
                    show['artist'] = link.get_text(strip=True)
                else:
                    h2 = title_div.find('h2')
                    if h2:
                        show['artist'] = h2.get_text(strip=True)
            if not show.get('artist'):
                h2 = container.find('h2')
                if h2:
                    show['artist'] = h2.get_text(strip=True)

            if not show.get('artist'):
                return None

            # Clean HTML entities
            show['artist'] = html.unescape(show['artist'])

            # Clean artist name (strip tour info, event keywords)
            full_title = show['artist']
            cleaned = self._clean_artist_name(full_title)
            if not cleaned:
                return None
            show['artist'] = cleaned

            # Extract date from separate eventMonth + eventDay spans
            date_month = container.find('span', class_='eventMonth')
            date_day = container.find('span', class_='eventDay')
            if date_month and date_day:
                month = date_month.get_text(strip=True)
                day = date_day.get_text(strip=True)
                show['date'] = self.format_date_standard(f"{month} {day}")
            else:
                # Fallback: try eventDate or singleEventDate
                date_elem = (container.find(id='eventDate')
                             or container.find(class_='eventMonth')
                             or container.find(class_='singleEventDate'))
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    match = re.search(r'(\w{3}),?\s+(\w{3})\s+(\d{1,2})', date_text)
                    if match:
                        show['date'] = f"{match.group(1)}, {match.group(2)} {match.group(3)}"
                    else:
                        show['date'] = self.format_date_standard(date_text)

            if not show.get('date'):
                show['date'] = 'TBD'

            # Extract times from container text
            container_text = container.get_text()

            doors = None
            doors_match = re.search(r'Doors?:?\s*(\d{1,2}(?::\d{2})?\s*[ap]m)', container_text, re.IGNORECASE)
            if doors_match:
                doors = doors_match.group(1).lower()
            show['doors'] = doors

            showtime = None
            show_match = re.search(r'Show:?\s*(\d{1,2}(?::\d{2})?\s*[ap]m)', container_text, re.IGNORECASE)
            if show_match:
                showtime = show_match.group(1).lower()
            show['showtime'] = showtime

            # Extract opener from h4 subheader (openers separated by <br> tags)
            opener = None
            subheader = container.find('h4', class_='eventSubHeader')
            if not subheader:
                subheader = container.find('h4')
            if subheader:
                # Use separator to handle <br>-separated names
                text = subheader.get_text(separator=', ', strip=True)
                text = html.unescape(text)
                # Strip leading "with" prefix
                text = re.sub(r'^with\s+', '', text, flags=re.IGNORECASE)
                # Skip descriptive text (not an opener name)
                if re.search(r'\b(anniversary|entirety|performing|celebration|album release)\b', text, re.IGNORECASE):
                    text = None
                if text and len(text) > 1 and len(text) < 150:
                    opener = text

            # Also check for "with" / "w/" in the original title
            if not opener:
                opener = self._extract_opener(full_title)

            show['opener'] = opener

            # Extract image
            img = container.find('img')
            if img:
                src = img.get('src') or img.get('data-src')
                if src:
                    if src.startswith('/'):
                        src = f"https://theorangepeel.net{src}"
                    show['image'] = src
            if not show.get('image'):
                show['image'] = None

            # Extract ticket URL (ETIX)
            ticket_link = container.find('a', href=lambda x: x and 'etix.com' in x)
            if ticket_link:
                show['ticket_url'] = ticket_link.get('href')
            else:
                # Try event page link as fallback
                event_link = container.find('a', href=lambda x: x and '/event/' in x)
                if event_link:
                    href = event_link.get('href')
                    if href:
                        if href.startswith('/'):
                            href = f"https://theorangepeel.net{href}"
                        show['ticket_url'] = href
            if not show.get('ticket_url'):
                show['ticket_url'] = None

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

        except Exception:
            return None

    # Additional event keywords for Orange Peel (comedy, contests, etc.)
    OP_EVENT_KEYWORDS = re.compile(
        r'\b(Comedy|Standup|Stand-Up|Contest|Roast|K-Pop Kids Party)\b',
        re.IGNORECASE
    )

    def _clean_artist_name(self, title):
        """Extract clean artist name from event title.

        Orange Peel titles use dashes for tour names and "+" for co-headliners:
        "Evan Honer – It's A Long Road Tour" → "Evan Honer"
        "Tab Benoit + Paul Thorn" → "Tab Benoit"
        """
        if not title or len(title) < 2:
            return None
        # Check event keywords on original name
        if self.EVENT_KEYWORDS.search(title):
            return None
        if self.OP_EVENT_KEYWORDS.search(title):
            return None
        if re.match(r'^R\.?I\.?P\.?\s', title):
            return None

        name = title
        # Strip colon + everything after
        name = re.sub(r':.*$', '', name)
        # Strip any dash followed by text containing "tour", "live", etc.
        tour_patterns = [
            r'\s*[-–—]\s*(.*tour.*|live.*|in concert.*|presents.*)$',
            r'\s*\(.*tour.*\)$',
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

        # Split on "+" for co-headliners (take first)
        if ' + ' in name:
            name = name.split(' + ')[0]

        # Split on " / " for multi-band bills (take first)
        name = re.sub(r'\s+/\s+.*$', '', name)

        # Strip parentheticals, "feat.", "ft.", comma-separated artists
        name = re.sub(r'\s*\([^)]*\)', '', name)
        name = re.sub(r'\s+feat[.:]\s+.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+ft[.:]\s+.*$', '', name, flags=re.IGNORECASE)
        name = re.sub(r',.*$', '', name)

        name = name.strip()
        return name if len(name) >= 2 else None

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


def main():
    scraper = OrangePeelScraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! The Orange Peel shows ready.")
    else:
        print("\nNo shows found. Check your connection and try again.")


if __name__ == "__main__":
    main()
