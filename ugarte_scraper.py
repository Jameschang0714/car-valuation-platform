import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from fake_useragent import UserAgent


class UgarteScraper:
    def __init__(self):
        self.base_url = "https://ugartecars.ph"
        self.inventory_url = f"{self.base_url}/inventory/"
        self.platform_name = "UgarteCars"

    def _extract_base_model(self, model):
        """Extract base model name, stripping variant/spec tokens.
        e.g. 'Mirage G4 1.2 GLX AT' -> 'Mirage G4'
        """
        if not model:
            return model
        spec_tokens = {
            'gls', 'glx', 'xle', 'xe', 'xls', 'ltd', 'sport', 'premium',
            'at', 'a/t', 'mt', 'm/t', 'cvt', 'dct', 'dsg',
            'gas', 'diesel', 'hybrid', 'ev',
            '4x2', '4x4', '2wd', '4wd', 'awd', 'fwd',
            'hb', 'sedan', 'wagon', 'van', 'suv', 'cab',
        }
        parts = model.split()
        base_parts = []
        for p in parts:
            if p.lower() in spec_tokens or re.match(r'^\d+\.\d+', p):
                break
            base_parts.append(p)
        return " ".join(base_parts) if base_parts else parts[0]

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
        """Parse UgarteCars inventory page HTML (MVL Motors Theme)."""
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        listings = []
        seen_links = set()

        # Strategy 1: MVL Motors Theme listing cards
        cards = soup.select('.listing-list-loop')
        if not cards:
            cards = soup.select('.stm-listing-directory-item, .stm-isotope-listing-item')

        for card in cards:
            # Title: MVL theme uses a.mvl_listing_title with .car-title inside
            title_elem = card.select_one('a.mvl_listing_title')
            title = ""
            href = ""

            if title_elem:
                href = title_elem.get('href', '')
                # Get full title from img alt (untruncated) or car-title div
                img = title_elem.select_one('.mvl_listing_logo img')
                if img and img.get('alt'):
                    title = img['alt'].strip()
                if not title:
                    car_title = title_elem.select_one('.car-title')
                    if car_title:
                        title = car_title.get_text(strip=True)
                if not title:
                    title = title_elem.get_text(strip=True)

            # Fallback title selectors
            if not title:
                for sel in ['.title a', 'h3 a', 'h2 a', '.content a']:
                    elem = card.select_one(sel)
                    if elem and elem.get_text(strip=True):
                        title = elem.get_text(strip=True)
                        href = elem.get('href', '') or href
                        break

            if not title or not href:
                continue

            if href in seen_links:
                continue
            seen_links.add(href)

            if not href.startswith('http'):
                href = urllib.parse.urljoin(self.base_url, href)

            # Price: MVL theme uses .mvl-normal-price
            price = 0
            price_elem = (
                card.select_one('.mvl-normal-price') or
                card.select_one('.normal-price') or
                card.select_one('.mvl-price') or
                card.select_one('.single-regular-price .h3') or
                card.select_one('.price')
            )
            if price_elem:
                price = self._parse_price(price_elem.get_text(strip=True))

            # Fallback: find any ₱ amount in the card text
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

        # Strategy 2: Fallback - find all links to /listings/ with prices nearby
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

    def _extract_date_from_page(self, url):
        """Fetch a listing page and extract datePublished from JSON-LD."""
        try:
            html = self._fetch_page(url)
            if not html:
                return None
            m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
            if m:
                return m.group(1)[:10]  # YYYY-MM-DD
        except Exception:
            pass
        return None

    def _enrich_dates(self, results, max_pages=10):
        """Batch-fetch listing pages in parallel to extract dates."""
        no_date = [(i, r) for i, r in enumerate(results) if r.get('date') == 'N/A' and r.get('link')]
        if not no_date:
            return results

        to_fetch = no_date[:max_pages]
        print(f"[UgarteCars] Enriching dates for {len(to_fetch)}/{len(no_date)} listings")

        with ThreadPoolExecutor(max_workers=min(5, len(to_fetch))) as executor:
            futures = {executor.submit(self._extract_date_from_page, r['link']): i for i, r in to_fetch}
            for future in futures:
                idx = futures[future]
                try:
                    date_str = future.result(timeout=8)
                    if date_str:
                        results[idx]['date'] = date_str
                except Exception:
                    pass

        return results

    def search(self, make, model, year, fuzzy_search=True):
        results = []
        target_year = int(year) if year and str(year).isdigit() else None
        base_model = self._extract_base_model(model) if model else ""

        try:
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] UgarteCars: Starting search for {make} {model} {year} (base_model={base_model})\n")

            all_listings = []

            # Strategy 1: Use search URL (Motors Theme search)
            # URL pattern: /inventory/{make_lower}/?stm_keywords={query}
            make_lower = make.lower().strip() if make else ""
            search_keywords = f"{year} {base_model}".strip()
            encoded_kw = urllib.parse.quote_plus(search_keywords)

            if make_lower:
                search_url = f"{self.inventory_url}{make_lower}/?stm_keywords={encoded_kw}"
            else:
                search_url = f"{self.inventory_url}?stm_keywords={encoded_kw}"

            print(f"[UgarteCars] Search URL: {search_url}")
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[UgarteCars] Search URL: {search_url}\n")

            html = self._fetch_page(search_url)
            all_listings = self._parse_listings(html)
            print(f"[UgarteCars] Search returned {len(all_listings)} listings")

            # Fallback: search without year
            if not all_listings and base_model:
                encoded_kw2 = urllib.parse.quote_plus(base_model)
                if make_lower:
                    search_url2 = f"{self.inventory_url}{make_lower}/?stm_keywords={encoded_kw2}"
                else:
                    search_url2 = f"{self.inventory_url}?stm_keywords={encoded_kw2}"
                print(f"[UgarteCars] Fallback without year: {search_url2}")
                html = self._fetch_page(search_url2)
                all_listings = self._parse_listings(html)

            # Fallback 2: brand-only inventory page crawl
            if not all_listings and make_lower:
                print(f"[UgarteCars] Fallback: crawling brand inventory pages")
                for page_num in range(1, 4):
                    if page_num == 1:
                        url = f"{self.inventory_url}{make_lower}/"
                    else:
                        url = f"{self.inventory_url}{make_lower}/page/{page_num}/"
                    html = self._fetch_page(url)
                    if not html:
                        break
                    page_listings = self._parse_listings(html)
                    if not page_listings:
                        break
                    all_listings.extend(page_listings)

            results = all_listings

            # Post-filter: base model keyword match
            if base_model and results:
                model_filtered = [r for r in results if base_model.lower() in r['title'].lower()]
                if model_filtered:
                    results = model_filtered

            # Post-filter: year matching
            if target_year and results:
                filtered = []
                for r in results:
                    listing_year = self._extract_year_from_title(r['title'])
                    if listing_year == 0:
                        filtered.append(r)  # Keep if no year in title
                    elif listing_year == target_year:
                        filtered.append(r)
                    elif fuzzy_search and abs(listing_year - target_year) <= 1:
                        filtered.append(r)
                if filtered:
                    results = filtered

            # Enrich dates from individual listing pages (parallel)
            if results:
                results = self._enrich_dates(results)
                print(f"[UgarteCars] Found {len(results)} matching listings")
            else:
                print(f"[UgarteCars] No matching results after filtering")

        except Exception as e:
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] UgarteCars Error: {e}\n")
            print(f"[UgarteCars] Error: {e}")

        return results
