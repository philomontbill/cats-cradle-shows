#!/usr/bin/env python3
"""
Heartwood Soundstage Scraper
Scrapes upcoming shows from heartwoodsoundstage.com

Site uses Webflow CMS with two collection lists on /shows:
- Hidden .ec-col-list-wrap: old calendar data (100-item cap, mostly past events)
- .uui-padding-vertical-large: upcoming shows grid with images, dates, times

We scrape the upcoming shows grid (List 4).
"""

import requests
from bs4 import BeautifulSoup
import re
from base_scraper import BaseScraper


class HeartwoodSoundstageScraper(BaseScraper):
    venue_name = "Heartwood Soundstage"
    venue_location = "Gainesville, FL"
    venue_website = "https://www.heartwoodsoundstage.com"
    output_filename = "data/shows-heartwoodsoundstage.json"

    def scrape_shows(self):
        """Main scraping function"""
        print("\nFetching events from Heartwood Soundstage...")

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
        """Fetch upcoming shows from the Webflow grid collection"""
        try:
            response = requests.get(
                'https://www.heartwoodsoundstage.com/shows',
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            shows = []

            # Upcoming shows grid — .uui-padding-vertical-large collection
            items = soup.select('.uui-padding-vertical-large .w-dyn-item')
            if not items:
                # Fallback: try all layout items
                items = soup.select('.uui-layout88_item')

            for item in items[:30]:
                show = self._parse_event(item)
                if show and show.get('artist'):
                    shows.append(show)

            return shows

        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def _parse_event(self, item):
        """Parse a single show card from the upcoming shows grid"""
        try:
            show = {
                'venue': self.venue_name
            }

            # Extract artist name from heading
            title_elem = item.select_one('h3')
            if not title_elem:
                title_elem = item.select_one('.uui-heading-xxsmall-2')
            if not title_elem:
                return None

            raw_title = title_elem.get_text().strip()
            if not raw_title:
                return None

            # Split "Artist with/w/ Opener" pattern
            artist, opener = self._split_artist_opener(raw_title)
            show['artist'] = artist
            if opener:
                show['opener'] = opener

            # Extract date from month + day stickers
            month_elem = item.select_one('.event-month')
            day_elem = item.select_one('.event-day')
            if month_elem and day_elem:
                month = month_elem.get_text().strip()
                day = day_elem.get_text().strip()
                show['date'] = self.format_date_standard(f"{month} {day}")
            else:
                show['date'] = 'TBD'

            # Extract show time
            time_elem = item.select_one('.event-time-new')
            if time_elem:
                time_text = time_elem.get_text().strip()
                if time_text:
                    show['showtime'] = time_text.lower()

            show['doors'] = None

            # Extract image
            img = item.select_one('img.image-40')
            if not img:
                img = item.select_one('img')
            if img:
                src = img.get('src') or img.get('data-src')
                if src:
                    show['image'] = src

            # Extract detail/ticket URL
            link = item.select_one('a.link-block-2')
            if not link:
                link = item.select_one('a[href*="/shows/"]')
            if link and link.get('href'):
                href = link['href']
                if href.startswith('/'):
                    href = f"https://www.heartwoodsoundstage.com{href}"
                show['ticket_url'] = href
            else:
                show['ticket_url'] = None

            show['notice'] = None

            return show

        except Exception as e:
            return None

    def _split_artist_opener(self, title):
        """Split title into artist and opener using 'with' or 'w/' pattern"""
        # Check for "w/" separator first (more specific)
        match = re.match(r'^(.+?)\s+w/\s+(.+)$', title, re.IGNORECASE)
        if match:
            artist = match.group(1).strip()
            opener = match.group(2).strip()
            if len(artist) > 2:
                return artist, opener

        # Check for "with" separator
        match = re.match(r'^(.+?)\s+with\s+(.+)$', title, re.IGNORECASE)
        if match:
            artist = match.group(1).strip()
            opener = match.group(2).strip()
            if len(artist) > 2:
                return artist, opener

        return title, None


def main():
    scraper = HeartwoodSoundstageScraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! Heartwood Soundstage shows ready.")
    else:
        print("\nNo shows found. Check connection and try again.")


if __name__ == "__main__":
    main()
