import re
import time
import urllib.parse
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from fake_useragent import UserAgent


class CarEmpireScraper:
    def __init__(self):
        self.base_url = "https://carempireph.com"
        self.platform_name = "CarEmpire"

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
            print(f"[CarEmpire] Warning: HTTP {response.status_code} for {url}")
            return ""
        except Exception as e:
            print(f"[CarEmpire] Error fetching {url}: {e}")
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

    def _parse_html(self, html):
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        listings = []

        # WooCommerce product structure
        products = soup.select('li.product, .product-type-simple, .type-product')
        if not products:
            # Broader fallback
            products = soup.select('.products .product')

        for product in products:
            # Title: WooCommerce uses h2.woocommerce-loop-product__title or similar
            title_elem = (
                product.select_one('.woocommerce-loop-product__title') or
                product.select_one('h2') or
                product.select_one('.product-title') or
                product.select_one('.card__heading')
            )

            # Price: WooCommerce price structure
            price_elem = (
                product.select_one('.price ins .woocommerce-Price-amount') or
                product.select_one('.price .woocommerce-Price-amount') or
                product.select_one('.price')
            )

            # Link
            link_elem = product.select_one('a[href*="/product/"]') or product.select_one('a')

            if title_elem and price_elem:
                title = title_elem.get_text(strip=True)
                price_text = price_elem.get_text(strip=True)
                price = self._parse_price(price_text)

                href = link_elem.get('href', '') if link_elem else ''
                if href and not href.startswith('http'):
                    href = urllib.parse.urljoin(self.base_url, href)

                if price > 50000:
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
            # Primary search: WooCommerce product search
            query = f"{make} {model}".strip()
            encoded_query = urllib.parse.quote_plus(query)
            search_url = f"{self.base_url}/?s={encoded_query}&post_type=product"

            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] CarEmpire: Searching {search_url}\n")

            html = self._fetch_page(search_url)
            results = self._parse_html(html)

            # Fallback: add year to query if no results
            if not results and year:
                query_with_year = f"{year} {make} {model}".strip()
                encoded_q2 = urllib.parse.quote_plus(query_with_year)
                search_url2 = f"{self.base_url}/?s={encoded_q2}&post_type=product"
                print(f"[CarEmpire] Fallback with year: {search_url2}")
                html = self._fetch_page(search_url2)
                results = self._parse_html(html)

            # Fallback 2: brand-only search
            if not results:
                encoded_make = urllib.parse.quote_plus(make)
                search_url3 = f"{self.base_url}/?s={encoded_make}&post_type=product"
                print(f"[CarEmpire] Fallback brand-only: {search_url3}")
                html = self._fetch_page(search_url3)
                all_brand = self._parse_html(html)
                # Filter by model keyword if provided
                if model:
                    results = [r for r in all_brand if model.lower() in r['title'].lower()]
                else:
                    results = all_brand

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
                results = filtered

            # Post-filter: model keyword match
            if model and results:
                results = [r for r in results if model.lower() in r['title'].lower()]

            if results:
                print(f"[CarEmpire] Found {len(results)} listings")
            else:
                print(f"[CarEmpire] No results found")

        except Exception as e:
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CarEmpire Error: {e}\n")
            print(f"[CarEmpire] Error: {e}")

        return results
