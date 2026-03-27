import re
import time
import urllib.parse
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from fake_useragent import UserAgent


class UgarteScraper:
    def __init__(self):
        self.base_url = "https://ugartecars.ph"
        self.inventory_url = f"{self.base_url}/inventory/"
        self.platform_name = "UgarteCars"

    def _fetch_page(self, url):
        ua = UserAgent(os=['windows', 'mac'], browsers=['chrome', 'edge'])
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.base_url
        }
        try:
            response = cffi_requests.get(url, headers=headers, impersonate="chrome120", timeout=15)
            if response.status_code == 200:
                return response.text
            print(f"[UgarteCars] Warning: HTTP {response.status_code} for {url}")
            return ""
        except Exception as e:
            print(f"[UgarteCars] Error fetching {url}: {e}")
            return ""

    def _parse_price(self, text):
        try:
            if not text:
                return 0
            clean_text = ''.join(c for c in text.split('.')[0] if c.isdigit())
            return int(clean_text) if clean_text else 0
        except Exception:
            return 0

    def _extract_year_from_title(self, title):
        match = re.search(r'\b(19\d{2}|20\d{2})\b', title)
        return int(match.group(1)) if match else 0

    def _parse_listings(self, html):
        """Parse UgarteCars inventory page HTML (Motors Theme / Elementor)."""
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        listings = []
        seen_links = set()

        # Strategy 1: Motors Theme listing cards
        cards = soup.select('.listing-list-loop, .stm-listing-directory-item')
        if not cards:
            # Strategy 2: Generic listing links with price
            cards = soup.select('.listing-card, .inventory-item, article.listing')

        for card in cards:
            # Title extraction
            title_elem = (
                card.select_one('.title a') or
                card.select_one('.listing-title a') or
                card.select_one('h3 a') or
                card.select_one('h2 a') or
                card.select_one('a.title')
            )

            # Price extraction - Motors theme uses various price wrappers
            price_elem = (
                card.select_one('.single-regular-price .h3') or
                card.select_one('.sale-price .h3') or
                card.select_one('.price .h3') or
                card.select_one('.regular-price') or
                card.select_one('.sale-price')
            )

            if title_elem:
                title = title_elem.get_text(strip=True)
                href = title_elem.get('href', '')

                if href in seen_links:
                    continue
                seen_links.add(href)

                if not href.startswith('http'):
                    href = urllib.parse.urljoin(self.base_url, href)

                price = 0
                if price_elem:
                    price = self._parse_price(price_elem.get_text(strip=True))

                # If no price from the card, try to find any ₱ amount in the card text
                if price == 0:
                    card_text = card.get_text()
                    price_match = re.search(r'₱\s*([\d,]+)', card_text)
                    if price_match:
                        price = self._parse_price(price_match.group(1))

                if price > 50000 and title:
                    listings.append({
                        'title': title,
                        'price': price,
                        'price_display': f"₱{price:,}",
                        'link': href,
                        'source': self.platform_name,
                        'date': 'N/A'
                    })

        # Strategy 3: Fallback - find all links to /listings/ with prices nearby
        if not listings:
            for link in soup.select('a[href*="/listings/"]'):
                href = link.get('href', '')
                title = link.get_text(strip=True)

                if not title or len(title) < 5 or href in seen_links:
                    continue
                seen_links.add(href)

                if not href.startswith('http'):
                    href = urllib.parse.urljoin(self.base_url, href)

                # Look for price in parent/sibling elements
                parent = link.find_parent(['div', 'article', 'li'])
                price = 0
                if parent:
                    price_match = re.search(r'₱\s*([\d,]+)', parent.get_text())
                    if price_match:
                        price = self._parse_price(price_match.group(1))

                if price > 50000 and title:
                    listings.append({
                        'title': title,
                        'price': price,
                        'price_display': f"₱{price:,}",
                        'link': href,
                        'source': self.platform_name,
                        'date': 'N/A'
                    })

        return listings

    def search(self, make, model, year, fuzzy_search=True):
        results = []
        target_year = int(year) if year and str(year).isdigit() else None

        try:
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] UgarteCars: Starting search for {make} {model} {year}\n")

            # Strategy 1: Crawl inventory pages and filter locally
            # (Ugarte uses AJAX filtering, so we crawl static pages instead)
            all_listings = []
            max_pages = 5  # Limit to avoid excessive crawling

            for page_num in range(1, max_pages + 1):
                if page_num == 1:
                    url = f"{self.inventory_url}?posts_per_page=20"
                else:
                    url = f"{self.inventory_url}page/{page_num}/?posts_per_page=20"

                print(f"[UgarteCars] Fetching page {page_num}...")
                html = self._fetch_page(url)
                if not html:
                    break

                page_listings = self._parse_listings(html)
                if not page_listings:
                    break  # No more results

                all_listings.extend(page_listings)
                print(f"[UgarteCars] Page {page_num}: {len(page_listings)} listings")

                # Stop early if we found enough
                if len(all_listings) >= 50:
                    break

            # Local filtering: brand match (required)
            if make:
                results = [r for r in all_listings if make.lower() in r['title'].lower()]
            else:
                results = all_listings

            # Model match
            if model and results:
                model_filtered = [r for r in results if model.lower() in r['title'].lower()]
                if model_filtered:
                    results = model_filtered

            # Year match
            if target_year and results:
                filtered = []
                for r in results:
                    listing_year = self._extract_year_from_title(r['title'])
                    if listing_year == 0:
                        continue  # Skip if we can't determine year
                    elif listing_year == target_year:
                        filtered.append(r)
                    elif fuzzy_search and abs(listing_year - target_year) <= 1:
                        filtered.append(r)
                if filtered:
                    results = filtered

            if results:
                print(f"[UgarteCars] Found {len(results)} matching listings")
            else:
                print(f"[UgarteCars] No matching results after filtering")

        except Exception as e:
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] UgarteCars Error: {e}\n")
            print(f"[UgarteCars] Error: {e}")

        return results
