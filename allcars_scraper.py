import asyncio
import re
import urllib.parse
import time
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from curl_cffi import requests as cffi_requests
from fake_useragent import UserAgent


class AllCarsScraper:
    def __init__(self):
        self.base_url = "https://allcarsph.com"
        self.search_url = f"{self.base_url}/search"
        self.platform_name = "AllCars.ph"
        self.target_year = None

    async def _fetch_page(self, url):
        ua = UserAgent(os=['windows', 'mac'], browsers=['chrome', 'edge'])
        headers = {
            "User-Agent": ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": self.base_url
        }
        try:
            async with AsyncSession(impersonate="chrome120") as session:
                response = await session.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    return response.text
                print(f"[AllCars] Warning: HTTP {response.status_code} for {url}")
                return ""
        except Exception as e:
            print(f"[AllCars] Error fetching {url}: {e}")
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

        cards = soup.select('.card-wrapper.product-card-wrapper')
        if not cards:
            cards = soup.select('.grid__item .card-wrapper')

        for card in cards:
            title_elem = card.select_one('.card__heading')
            price_elem = card.select_one('.price-item--sale, .price-item--regular, .price-item')
            link_elem = card.select_one('a')

            badge = card.select_one('.badge')
            if badge and 'sold' in badge.text.lower():
                continue

            if title_elem and price_elem:
                title = title_elem.text.strip()
                price = self._parse_price(price_elem.text.strip())
                href = link_elem.get('href') if link_elem else None
                url = urllib.parse.urljoin(self.base_url, href) if href else ""

                if price > 50000:
                    listing_year = self._extract_year_from_title(title)
                    if self.target_year and listing_year:
                        if abs(self.target_year - listing_year) > 1:
                            continue

                    listings.append({
                        'title': title,
                        'price': price,
                        'price_display': f"₱{price:,}",
                        'link': url,
                        'source': self.platform_name,
                        'date': 'N/A'
                    })
        return listings

    _SPEC_TOKENS = {
        'a/t', 'at', 'm/t', 'mt', 'gas', 'diesel', 'dsl',
        'automatic', 'manual', '4x4', '4x2', '2wd', '4wd',
        'turbo', 'hybrid', '-', 'cvt',
    }

    def _build_search_tokens(self, query):
        year_match = re.search(r'\b(19|20)\d{2}\b', query)
        year = year_match.group(0) if year_match else ""
        if year:
            self.target_year = int(year)

        remaining = [p for p in query.split() if p != year]
        tokens = []
        for p in remaining:
            if p.lower() in self._SPEC_TOKENS or re.match(r'^\d+\.\d+$', p):
                break
            tokens.append(p)
            if len(tokens) >= 3:
                break
        return year, tokens

    async def _async_search(self, query):
        year, tokens = self._build_search_tokens(query)
        clean_query = " ".join(tokens) if tokens else query

        print(f"[{self.platform_name}] Query: '{clean_query}' (Original: '{query}')")

        encoded_query = urllib.parse.quote_plus(clean_query)
        search_url = f"{self.search_url}?type=product&q={encoded_query}"

        html = await self._fetch_page(search_url)
        listings = self._parse_html(html)

        # Fallback 1: Brand + Model only (2 tokens)
        if not listings and len(tokens) > 2:
            fallback_query = " ".join(tokens[:2])
            print(f"[{self.platform_name}] Fallback to 2-token: '{fallback_query}'")
            encoded_fb = urllib.parse.quote_plus(fallback_query)
            html = await self._fetch_page(f"{self.search_url}?type=product&q={encoded_fb}")
            listings = self._parse_html(html)

        # Fallback 2: Model only
        if not listings and len(tokens) > 1:
            model_only = tokens[1]
            print(f"[{self.platform_name}] Fallback to model only: '{model_only}'")
            encoded_m = urllib.parse.quote_plus(model_only)
            html = await self._fetch_page(f"{self.search_url}?type=product&q={encoded_m}")
            listings = self._parse_html(html)

        # Post-filter: year ±1 and model keyword
        if listings and self.target_year and len(tokens) >= 2:
            key_model = tokens[1].lower()
            before = len(listings)
            filtered = []
            for item in listings:
                title = item.get("title", "").lower()
                if key_model not in title:
                    continue
                lyr = self._extract_year_from_title(item.get("title", ""))
                if lyr > 0 and abs(lyr - self.target_year) > 1:
                    continue
                filtered.append(item)
            listings = filtered
            if before != len(listings):
                print(f"[{self.platform_name}] Year/model filter: {before} -> {len(listings)}")

        if listings:
            try:
                print(f"[{self.platform_name}] Found {len(listings)} listings. Top: PHP {listings[0]['price']:,}")
            except Exception:
                pass

        await asyncio.sleep(1)
        return listings

    def search(self, make, model, year, fuzzy_search=True):
        """Sync interface matching other scrapers. Internally runs async."""
        query = f"{year} {make} {model}".strip()
        self.target_year = int(year) if year and str(year).isdigit() else None

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(self._async_search(query))
            loop.close()
        except Exception as e:
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] AllCars Error: {e}\n")
            print(f"[AllCars] Error: {e}")
            results = []

        return results
