#!/usr/bin/env python3
"""
Motorco Music Hall Scraper
Scrapes upcoming shows from motorcomusic.com RSS feed (Durham, NC)
"""

import requests
from bs4 import BeautifulSoup
import re
import html
from datetime import datetime
from base_scraper import BaseScraper


class MotorcoScraper(BaseScraper):
    venue_name = "Motorco Music Hall"
    venue_location = "Durham, NC"
    venue_website = "https://motorcomusic.com"
    output_filename = "shows-motorco.json"

    def scrape_shows(self):
        """Main scraping function"""
        print("\nFetching events from Motorco RSS feed...")

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
        """Fetch and parse events from RSS feed"""
        try:
            response = requests.get(
                'https://motorcomusic.com/feed/',
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'xml')
            shows = []

            items = soup.find_all('item')

            for item in items[:30]:
                show = self._parse_item(item)
                if show and show.get('artist'):
                    shows.append(show)

            return shows

        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def _parse_item(self, item):
        """Parse a single RSS item"""
        try:
            show = {
                'venue': self.venue_name
            }

            # Extract artist name from title
            title_elem = item.find('title')
            if title_elem:
                title = title_elem.get_text().strip()
                # Clean up HTML entities
                title = html.unescape(title)
                # Title format is often "ARTIST : TOUR NAME" - extract artist
                if ' : ' in title:
                    show['artist'] = title.split(' : ')[0].strip()
                else:
                    show['artist'] = title

            if not show.get('artist'):
                return None

            # Extract event URL
            link_elem = item.find('link')
            if link_elem:
                show['ticket_url'] = link_elem.get_text().strip()

            # Extract date from content
            content_elem = item.find('content:encoded') or item.find('encoded')
            if content_elem:
                content = content_elem.get_text()

                # Look for date pattern like "Sat Mar 7, 2026 7:30 pm"
                date_match = re.search(
                    r'(\w{3})\s+(\w{3})\s+(\d{1,2}),?\s+(\d{4})\s+(\d{1,2}:\d{2}\s*[ap]m)',
                    content, re.IGNORECASE
                )
                if date_match:
                    day_name = date_match.group(1)
                    month = date_match.group(2)
                    day = date_match.group(3)
                    show['date'] = f"{day_name}, {month} {day}"
                    show['showtime'] = date_match.group(5).lower()
                else:
                    # Fallback to pubDate
                    pub_date = item.find('pubDate')
                    if pub_date:
                        show['date'] = self._parse_pub_date(pub_date.get_text())

                # Look for opener in "with" section
                with_match = re.search(r'<span class="with">with</span>\s*([^<]+)', content)
                if with_match:
                    opener = with_match.group(1).strip()
                    if opener and opener.upper() != 'SUPPORT' and len(opener) > 2:
                        show['opener'] = html.unescape(opener)

            if not show.get('date'):
                show['date'] = 'TBD'

            # Try to get image from event page
            if show.get('ticket_url'):
                show['image'] = self._get_event_image(show['ticket_url'])

            show['notice'] = None
            show['doors'] = None

            return show

        except Exception as e:
            return None

    def _parse_pub_date(self, pub_date_str):
        """Parse RSS pubDate to standard format"""
        try:
            # Format: "Sat, 07 Mar 2026 00:00:00 +0000"
            parsed = datetime.strptime(pub_date_str[:16], "%a, %d %b %Y")
            return parsed.strftime("%a, %b %d")
        except:
            return 'TBD'

    def _get_event_image(self, url):
        """Fetch event page to get image"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Try og:image first
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    return og_image['content']

                # Try featured image
                img = soup.select_one('.wp-post-image, .event-image img, article img')
                if img:
                    src = img.get('src')
                    if src and 'logo' not in src.lower():
                        return src
        except:
            pass
        return None


def main():
    scraper = MotorcoScraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! Motorco shows ready.")
    else:
        print("\nNo shows found. Check connection and try again.")


if __name__ == "__main__":
    main()
