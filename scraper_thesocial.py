#!/usr/bin/env python3
"""
The Social (Orlando) Show Scraper with YouTube Integration
Fetches shows from TKX ticketing platform and finds YouTube videos for each artist
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from base_scraper import BaseScraper


class TheSocialScraper(BaseScraper):
    venue_name = "The Social"
    venue_location = "Orlando, FL"
    venue_website = "https://www.thesocial.org"
    output_filename = "shows-thesocial.json"

    def __init__(self):
        super().__init__()
        # TKX venue filter ID for The Social
        self.tkx_url = "https://tkx.live/events/?filter_venue%5B%5D=2450"

    def scrape_shows(self):
        """Main scraping function"""
        print("\nFetching events from TKX...")

        try:
            response = requests.get(
                self.tkx_url,
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Error fetching page: {e}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find all event tiles
        event_tiles = soup.find_all('div', class_='event-tile')

        if not event_tiles:
            print("No events found")
            return []

        print(f"Found {len(event_tiles)} events\n")

        # Extract event URLs and fetch details
        shows = []
        for tile in event_tiles[:25]:
            show = self._process_event_tile(tile)
            if show:
                shows.append(show)
            time.sleep(0.5)

        # Add YouTube videos with progress output
        shows = self.process_shows_with_youtube(shows)

        # Save to JSON
        self.save_json(shows)

        return shows

    def _process_event_tile(self, tile):
        """Process a single event tile into our format"""
        try:
            # Get event link
            link = tile.find('a', class_='event-tile-link')
            if not link:
                return None

            event_url = link.get('href')

            # Get data from the share button (has clean data attributes)
            share_btn = tile.find('button', class_='share')
            if share_btn:
                artist = share_btn.get('data-artist') or share_btn.get('data-title')
                date_str = share_btn.get('data-date', '')
            else:
                # Fall back to the artist div
                artist_div = tile.find('div', class_='artist')
                artist = artist_div.get_text(strip=True) if artist_div else None

                # Get date from date div
                date_div = tile.find('div', class_='date')
                if date_div:
                    month = date_div.find('div', class_='month')
                    day = date_div.find('div', class_='day')
                    month_text = month.get_text(strip=True) if month else ''
                    day_text = day.get_text(strip=True) if day else ''
                    date_str = f"{month_text} {day_text}"
                else:
                    date_str = ''

            if not artist:
                return None

            # Clean up artist name
            artist = self._clean_artist_name(artist)

            # Format date (input: MM/DD/YYYY from share button)
            if date_str:
                date = self.format_date_standard(date_str, "%m/%d/%Y")
            else:
                date = "TBD"

            # Get image from background-image style
            image = None
            style = tile.get('style', '')
            img_match = re.search(r'background-image:\s*url\([\'"]?([^\'")\s]+)[\'"]?\)', style)
            if img_match:
                image = img_match.group(1)

            # Get venue/time info from categories
            categories_div = tile.find('div', class_='categories')
            showtime = None
            if categories_div:
                cat_text = categories_div.get_text(strip=True)
                # Extract time like "7:00pm"
                time_match = re.search(r'(\d{1,2}:\d{2}\s*[ap]m)', cat_text, re.IGNORECASE)
                if time_match:
                    showtime = time_match.group(1).lower()

            return {
                'artist': artist,
                'date': date,
                'venue': 'The Social',
                'opener': None,
                'notice': None,
                'doors': None,
                'showtime': showtime,
                'image': image,
                'ticket_url': event_url
            }

        except Exception as e:
            return None

    def _fetch_event_page(self, url):
        """Fetch individual event page for more details"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Get artist from title
            title = soup.find('h1')
            artist = title.get_text(strip=True) if title else None

            # Get date
            date_elem = soup.find('span', class_='event-date') or soup.find(class_='date')
            date = date_elem.get_text(strip=True) if date_elem else None

            # Get image
            og_image = soup.find('meta', property='og:image')
            image = og_image.get('content') if og_image else None

            return {
                'artist': artist,
                'date': date,
                'image': image
            }

        except Exception:
            return None

    def _clean_artist_name(self, title):
        """Extract clean artist name from event title"""
        if not title:
            return None

        # Remove common tour/event suffixes
        patterns = [
            r'\s*[-–—]\s*(.*tour.*|live.*|in concert.*|presents.*)$',
            r'\s*\(.*tour.*\)$',
            r'\s*:\s*.*tour.*$',
            r'\s+tour$',
        ]

        name = title
        for pattern in patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)

        # Handle "with" for openers - take part before "with"
        if ' with ' in name.lower():
            name = re.split(r'\s+with\s+', name, flags=re.IGNORECASE)[0]
        if ' w/ ' in name.lower():
            name = re.split(r'\s+w/\s+', name, flags=re.IGNORECASE)[0]

        return name.strip()


def main():
    scraper = TheSocialScraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! The Social shows ready.")
    else:
        print("\nNo shows found. Check your connection and try again.")


if __name__ == "__main__":
    main()
