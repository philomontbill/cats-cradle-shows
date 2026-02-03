#!/usr/bin/env python3
"""
Cat's Cradle Show Scraper with YouTube Integration
Scrapes upcoming shows and finds YouTube videos for each artist
"""

import requests
from bs4 import BeautifulSoup
import re
import time
from base_scraper import BaseScraper


class CatsCradleScraper(BaseScraper):
    venue_name = "Cat's Cradle"
    venue_location = "Carrboro, NC"
    venue_website = "https://catscradle.com"
    output_filename = "shows-catscradle.json"

    def scrape_shows(self):
        """Main scraping function"""
        print("\nFetching event list...")
        event_urls = self._get_event_urls()

        if not event_urls:
            print("No events found")
            return []

        print(f"Found {len(event_urls)} events\n")

        shows = []
        for url in event_urls[:25]:
            show = self._extract_show_data(url)
            if show:
                shows.append(show)
            time.sleep(1)  # Respectful delay

        # Add YouTube videos
        shows = self.process_shows_with_youtube(shows)

        # Sort by date
        shows = self.sort_shows_by_date(shows)

        # Save to JSON
        self.save_json(shows)

        return shows

    def _get_event_urls(self):
        """Get all event URLs from the main events page"""
        try:
            response = requests.get(
                'https://catscradle.com/events/',
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            urls = []

            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if '/event/' in href:
                    if href.startswith('/'):
                        href = f"https://catscradle.com{href}"
                    if 'catscradle.com' in href and href not in urls:
                        urls.append(href)

            return urls

        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def _extract_show_data(self, url):
        """Extract show details from an event page"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            artist = self._extract_artist_name(soup)
            if not artist:
                return None

            notice = self._extract_notice(soup)
            date = self._extract_date(soup)
            venue = self._extract_venue(soup, url)
            opener = self._extract_opener(soup)

            # If opener looks like a notice, move it
            if opener and re.search(r'rescheduled|postponed|cancelled|canceled|new date', opener, re.IGNORECASE):
                if not notice:
                    notice = opener
                opener = None

            doors_time, show_time = self._extract_times(soup)
            image = self._extract_image(soup)

            return {
                'artist': artist,
                'date': date,
                'venue': venue,
                'opener': opener,
                'notice': notice,
                'doors': doors_time,
                'showtime': show_time,
                'image': image,
                'event_url': url
            }

        except Exception:
            return None

    def _extract_artist_name(self, soup):
        """Extract the main artist name"""
        h1 = soup.find('h1')
        if h1:
            text = h1.get_text().strip()
            name = re.split(r'\s+at\s+|\s+\|\s+', text, flags=re.IGNORECASE)[0]
            name = name.strip()
            if name and len(name) > 1:
                return name

        title = soup.find('title')
        if title:
            text = title.get_text().strip()
            name = re.split(r'\s+at\s+|\s+\|\s+|\s+-\s+Cat', text, flags=re.IGNORECASE)[0]
            name = name.strip()
            if name and len(name) > 1 and 'cat' not in name.lower():
                return name

        return None

    def _extract_notice(self, soup):
        """Extract notice/alert line"""
        try:
            text = soup.get_text()
            notice_patterns = [
                r'(rescheduled[^.]*)',
                r'(postponed[^.]*)',
                r'(cancelled[^.]*)',
                r'(canceled[^.]*)',
                r'(sold out)',
                r'(new date[^.]*)',
                r"(cat'?s cradle presents)",
            ]

            for pattern in notice_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    notice = match.group(1).strip()
                    if len(notice) < 80:
                        return notice

            return None
        except Exception:
            return None

    def _extract_date(self, soup):
        """Extract the show date"""
        text = soup.get_text()

        patterns = [
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+'
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self.format_date_standard(match.group())

        return "TBD"

    def _extract_venue(self, soup, url=''):
        """Determine which venue section"""
        text = soup.get_text().lower()
        url_lower = url.lower()

        if 'motorco' in text or 'motorco' in url_lower:
            return "Motorco Music Hall"
        elif 'back room' in text:
            return "Cat's Cradle Back Room"
        elif 'haw river' in text or 'ballroom' in text:
            return "Haw River Ballroom"
        else:
            return "Cat's Cradle"

    def _extract_opener(self, soup):
        """Extract opening act from the page"""
        try:
            skip_patterns = [
                'door', 'show', 'ticket', 'buy', 'pm', 'am', 'carrboro', 'saxapahaw',
                'venue', 'location', 'address', 'cat\'s cradle', 'presents', 'haw river',
                'friday', 'saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday'
            ]

            def is_valid_opener(text):
                if not text or len(text) < 3 or len(text) > 150:
                    return False
                text_lower = text.lower()
                return not any(skip in text_lower for skip in skip_patterns)

            # Method 1: Look for h4 tag
            h4_tags = soup.find_all('h4')
            for h4 in h4_tags:
                text = h4.get_text().strip()
                if is_valid_opener(text):
                    return text

            # Method 2: Look for "with" pattern in ticket URL
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'etix.com' in href and 'with' in href.lower():
                    match = re.search(r'with[_-]?([a-z\-]+)-(?:carrboro|saxapahaw)', href.lower())
                    if match:
                        opener_slug = match.group(1)
                        opener = opener_slug.replace('-', ' ').title()
                        if is_valid_opener(opener):
                            return opener

            # Method 3: Look for "with [Name]" pattern in page text
            text = soup.get_text()
            with_match = re.search(r'\bwith\s+([A-Z][A-Za-z\s&\'\-\.]+?)(?:\s*\n|\s*Doors|\s*Show|\s*\d|\s*$)', text)
            if with_match:
                opener = with_match.group(1).strip()
                if is_valid_opener(opener):
                    return opener

            return None

        except Exception:
            return None

    def _extract_times(self, soup):
        """Extract door time and show time"""
        try:
            text = soup.get_text()

            doors_time = None
            show_time = None

            doors_match = re.search(r'Doors:?\s*(\d{1,2}(?::\d{2})?\s*[ap]m)', text, re.IGNORECASE)
            if doors_match:
                doors_time = doors_match.group(1).strip()

            show_match = re.search(r'Show:?\s*(\d{1,2}(?::\d{2})?\s*[ap]m)', text, re.IGNORECASE)
            if show_match:
                show_time = show_match.group(1).strip()

            return doors_time, show_time

        except Exception:
            return None, None

    def _extract_image(self, soup):
        """Extract artist/event image from the page"""
        try:
            selectors = [
                'img.wp-post-image',
                '.event-image img',
                '.featured-image img',
                'article img',
                '.entry-content img',
                'img[src*="event"]',
                'img[src*="upload"]',
            ]

            for selector in selectors:
                img = soup.select_one(selector)
                if img:
                    src = img.get('src') or img.get('data-src')
                    if src:
                        if src.startswith('//'):
                            src = f"https:{src}"
                        elif src.startswith('/'):
                            src = f"https://catscradle.com{src}"

                        if any(skip in src.lower() for skip in ['logo', 'icon', 'avatar', '1x1']):
                            continue

                        if any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) or 'cdn' in src.lower():
                            return src

            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                return og_image['content']

            return None

        except Exception:
            return None


def main():
    scraper = CatsCradleScraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! Open index.html in a browser to view shows.")
    else:
        print("\nNo shows found. Check your connection and try again.")


if __name__ == "__main__":
    main()
