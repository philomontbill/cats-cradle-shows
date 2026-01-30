#!/usr/bin/env python3
"""
Cat's Cradle Show Scraper with YouTube Integration
Scrapes upcoming shows and finds YouTube videos for each artist
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import time
from datetime import datetime
from urllib.parse import quote_plus


class CatsCradleScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.overrides = self.load_overrides()
        print("Cat's Cradle Show Scraper")
        print("=" * 40)

    def load_overrides(self):
        """Load manual YouTube overrides from overrides.json"""
        try:
            with open('overrides.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"artist_youtube": {}, "opener_youtube": {}}

    def scrape_shows(self):
        """Main scraping function"""
        print("\nFetching event list...")
        event_urls = self.get_event_urls()

        if not event_urls:
            print("No events found")
            return []

        print(f"Found {len(event_urls)} events\n")

        shows = []
        for i, url in enumerate(event_urls[:25], 1):  # Limit to 25 shows
            print(f"[{i}/{min(len(event_urls), 25)}] Processing...")

            show = self.extract_show_data(url)
            if show:
                # Check for manual override first, then search YouTube
                artist_overrides = self.overrides.get('artist_youtube', {})
                if show['artist'] in artist_overrides:
                    video_id = artist_overrides[show['artist']]
                else:
                    video_id = self.search_youtube(show['artist'])
                show['youtube_id'] = video_id

                # Search YouTube for the opener if there is one
                if show.get('opener'):
                    opener_overrides = self.overrides.get('opener_youtube', {})
                    if show['opener'] in opener_overrides:
                        opener_video_id = opener_overrides[show['opener']]
                    else:
                        opener_video_id = self.search_youtube(show['opener'])
                    show['opener_youtube_id'] = opener_video_id

                print(f"  -> {show['artist']} ({show['date']})")
                if show.get('opener'):
                    opener_yt = show.get('opener_youtube_id')
                    print(f"     Opener: {show['opener']} {f'(YT: {opener_yt})' if opener_yt else '(no video)'}")
                if show.get('doors') or show.get('showtime'):
                    print(f"     Times: Doors {show.get('doors', 'N/A')} / Show {show.get('showtime', 'N/A')}")
                if show.get('image'):
                    print(f"     Image: Found")
                if video_id:
                    print(f"     YouTube: {video_id}")
                else:
                    print(f"     YouTube: No video found")

                shows.append(show)

            time.sleep(1)  # Respectful delay

        # Sort by date
        shows = self.sort_by_date(shows)

        # Save to JSON
        self.save_json(shows)

        return shows

    def get_event_urls(self):
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
                    if href not in urls:
                        urls.append(href)

            return urls

        except Exception as e:
            print(f"Error fetching events: {e}")
            return []

    def extract_show_data(self, url):
        """Extract show details from an event page"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract artist name
            artist = self.extract_artist_name(soup)
            if not artist:
                return None

            # Extract date
            date = self.extract_date(soup)

            # Extract venue
            venue = self.extract_venue(soup)

            # Extract opener
            opener = self.extract_opener(soup)

            # Extract door and show times
            doors_time, show_time = self.extract_times(soup)

            # Extract artist image
            image = self.extract_image(soup)

            return {
                'artist': artist,
                'date': date,
                'venue': venue,
                'opener': opener,
                'doors': doors_time,
                'showtime': show_time,
                'image': image,
                'event_url': url
            }

        except Exception as e:
            return None

    def extract_artist_name(self, soup):
        """Extract the main artist name"""
        # Try h1 first
        h1 = soup.find('h1')
        if h1:
            text = h1.get_text().strip()
            # Clean up - remove venue info after "at"
            name = re.split(r'\s+at\s+|\s+\|\s+', text, flags=re.IGNORECASE)[0]
            name = name.strip()
            if name and len(name) > 1:
                return name

        # Try title tag
        title = soup.find('title')
        if title:
            text = title.get_text().strip()
            name = re.split(r'\s+at\s+|\s+\|\s+|\s+-\s+Cat', text, flags=re.IGNORECASE)[0]
            name = name.strip()
            if name and len(name) > 1 and 'cat' not in name.lower():
                return name

        return None

    def extract_date(self, soup):
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
                return self.format_date(match.group())

        return "TBD"

    def format_date(self, date_str):
        """Convert to a standard format"""
        try:
            clean = re.sub(r',\s*', ' ', date_str).strip()

            formats = [
                "%A %B %d",
                "%A %b %d",
                "%B %d %Y",
                "%b %d %Y",
                "%B %d",
                "%b %d"
            ]

            today = datetime.now().date()
            current_year = today.year

            for fmt in formats:
                try:
                    parsed = datetime.strptime(clean, fmt)
                    # Use current year, or next year if date has passed
                    parsed = parsed.replace(year=current_year)
                    if parsed.date() < today:
                        parsed = parsed.replace(year=current_year + 1)
                    return parsed.strftime("%a, %b %d")
                except ValueError:
                    continue

            return date_str
        except:
            return date_str

    def extract_venue(self, soup):
        """Determine which venue section"""
        text = soup.get_text().lower()

        if 'back room' in text:
            return "Cat's Cradle Back Room"
        elif 'haw river' in text or 'ballroom' in text:
            return "Haw River Ballroom"
        else:
            return "Cat's Cradle"

    def extract_opener(self, soup):
        """Extract opening act from the page"""
        try:
            # Skip patterns - these are not openers
            skip_patterns = [
                'door', 'show', 'ticket', 'buy', 'pm', 'am', 'carrboro', 'saxapahaw',
                'venue', 'location', 'address', 'cat\'s cradle', 'presents', 'haw river',
                'friday', 'saturday', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday'
            ]

            def is_valid_opener(text):
                if not text or len(text) < 3 or len(text) > 50:
                    return False
                text_lower = text.lower()
                return not any(skip in text_lower for skip in skip_patterns)

            # Method 1: Look for h4 tag (Cat's Cradle puts opener in h4)
            h4_tags = soup.find_all('h4')
            for h4 in h4_tags:
                text = h4.get_text().strip()
                if is_valid_opener(text):
                    return text

            # Method 2: Look for "with" pattern in ticket URL
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'etix.com' in href and 'with' in href.lower():
                    # Extract opener from URL like "jonah-kagenwith-anna-graves-carrboro"
                    match = re.search(r'with[_-]?([a-z\-]+)-(?:carrboro|saxapahaw)', href.lower())
                    if match:
                        opener_slug = match.group(1)
                        # Convert slug to name (replace hyphens with spaces, title case)
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

    def extract_times(self, soup):
        """Extract door time and show time"""
        try:
            text = soup.get_text()

            doors_time = None
            show_time = None

            # Look for "Doors: X pm" pattern
            doors_match = re.search(r'Doors:?\s*(\d{1,2}(?::\d{2})?\s*[ap]m)', text, re.IGNORECASE)
            if doors_match:
                doors_time = doors_match.group(1).strip()

            # Look for "Show: X pm" pattern
            show_match = re.search(r'Show:?\s*(\d{1,2}(?::\d{2})?\s*[ap]m)', text, re.IGNORECASE)
            if show_match:
                show_time = show_match.group(1).strip()

            return doors_time, show_time

        except Exception:
            return None, None

    def extract_image(self, soup):
        """Extract artist/event image from the page"""
        try:
            # Try various selectors that Cat's Cradle might use
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
                        # Make sure it's an absolute URL
                        if src.startswith('//'):
                            src = f"https:{src}"
                        elif src.startswith('/'):
                            src = f"https://catscradle.com{src}"

                        # Skip tiny images, icons, logos
                        if any(skip in src.lower() for skip in ['logo', 'icon', 'avatar', '1x1']):
                            continue

                        # Check for valid image extension or CDN URL
                        if any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) or 'cdn' in src.lower():
                            return src

            # Also try Open Graph image (often used for social sharing)
            og_image = soup.find('meta', property='og:image')
            if og_image and og_image.get('content'):
                return og_image['content']

            return None

        except Exception:
            return None

    def search_youtube(self, artist_name):
        """Search YouTube for artist's music by scraping search results"""
        try:
            # Clean up artist name for search
            # Remove common show title patterns
            clean_name = re.sub(r'\s*[-–]\s*(Tour|Live|Concert|Show|Anniversary|Tribute|Benefit|Dance|Jam|Bash).*$', '', artist_name, flags=re.IGNORECASE)
            clean_name = re.sub(r'\s*\d+(st|nd|rd|th)\s+Annual.*$', '', clean_name, flags=re.IGNORECASE)
            clean_name = re.sub(r',.*$', '', clean_name)  # Remove everything after comma (often support acts)
            clean_name = clean_name.strip()

            if len(clean_name) < 2:
                return None

            # Try multiple search strategies to find the band, not a song with same name
            search_queries = [
                f"{clean_name} band official video",
                f"{clean_name} band music",
                f"{clean_name} official music video",
            ]

            for query_text in search_queries:
                query = quote_plus(query_text)
                url = f"https://www.youtube.com/results?search_query={query}"

                response = requests.get(url, headers=self.headers, timeout=10)

                if response.status_code == 200:
                    # Look for video IDs in the response
                    patterns = [
                        r'"videoId":"([a-zA-Z0-9_-]{11})"',
                        r'/watch\?v=([a-zA-Z0-9_-]{11})',
                    ]

                    for pattern in patterns:
                        matches = re.findall(pattern, response.text)
                        if matches:
                            return matches[0]

                time.sleep(0.5)  # Brief delay between searches

            return None

        except Exception as e:
            return None

    def sort_by_date(self, shows):
        """Sort shows chronologically"""
        current_year = datetime.now().year

        def date_key(show):
            date_str = show.get('date', 'TBD')
            if date_str == 'TBD':
                return datetime(2099, 12, 31)

            try:
                parsed = datetime.strptime(f"{date_str}, {current_year}", "%a, %b %d, %Y")
                return parsed
            except:
                return datetime(2099, 12, 31)

        return sorted(shows, key=date_key)

    def save_json(self, shows):
        """Save shows to JSON file"""
        data = {
            'venue': {
                'name': "Cat's Cradle",
                'location': 'Carrboro, NC',
                'website': 'https://catscradle.com'
            },
            'shows': shows,
            'total_shows': len(shows),
            'shows_with_video': sum(1 for s in shows if s.get('youtube_id')),
            'shows_with_image': sum(1 for s in shows if s.get('image')),
            'last_updated': datetime.now().isoformat()
        }

        with open('shows.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nSaved {len(shows)} shows to shows.json")
        print(f"  - {data['shows_with_video']} have YouTube videos")
        print(f"  - {data['shows_with_image']} have images")


def main():
    scraper = CatsCradleScraper()
    shows = scraper.scrape_shows()

    if shows:
        print("\nDone! Open index.html in a browser to view shows.")
    else:
        print("\nNo shows found. Check your connection and try again.")


if __name__ == "__main__":
    main()
