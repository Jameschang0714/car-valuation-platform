import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
from fake_useragent import UserAgent
import time
import random

class PhilkotseScraper:
    def __init__(self):
        self.base_url = "https://philkotse.com"
        self.ua = UserAgent()

    def search(self, make, model, year, fuzzy_search=True):
        search_items = []
        
        # Format strings for URLs
        make_slug = make.lower().replace(" ", "-")
        model_slug = model.lower().replace(" ", "-")
        target_year = int(year)
        
        # Define paths to search
        paths = [
            f"/{make_slug}-{model_slug}-year-{target_year}-for-sale",
            f"/infinite-scroll/used-{make_slug}-{model_slug}-for-sale?pageIndex=1",
            f"/cars-for-sale?q={urllib.parse.quote(f'{make} {model} {target_year}')}"
        ]
        
        # If fuzzy search is enabled and we need more results, we add adjacent years
        search_years = [target_year]
        if fuzzy_search:
            search_years.extend([target_year - 1, target_year + 1])
            for fy in [target_year - 1, target_year + 1]:
                paths.append(f"/{make_slug}-{model_slug}-year-{fy}-for-sale")

        # Deduplicate paths while preserving order
        unique_paths = []
        for p in paths:
            if p not in unique_paths: unique_paths.append(p)

        for path in unique_paths:
            url = self.base_url + path if not path.startswith("http") else path
            
            headers = {
                "User-Agent": self.ua.random,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Referer": self.base_url
            }
            
            try:
                time.sleep(random.uniform(0.5, 1.5))
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code != 200: continue

                soup = BeautifulSoup(response.text, 'html.parser')
                listings = soup.select('.col-4, .list-car-item, .item, .car-item')
                
                for item in listings:
                    try:
                        title_elem = item.select_one('h3.title, .item-title, .title, a[title]')
                        price_elem = item.select_one('.price, .item-price, .amount')
                        link_elem = item.select_one('a[href*="/"]')

                        if title_elem and price_elem:
                            title = title_elem.get_text(strip=True)
                            price_text = price_elem.get_text(strip=True)
                            link = link_elem['href'] if link_elem else ""
                            
                            if link and not link.startswith('http'):
                                link = self.base_url + link
                            
                            # Validation: must contain model
                            if model.lower() in title.lower():
                                # Match ANY of the target years
                                matched_year = any(str(y) in title for y in search_years)
                                if matched_year:
                                    price = self._parse_price(price_text)
                                    if price > 30000:
                                            search_items.append({
                                                'title': title,
                                                'price': price,
                                                'price_display': price_text,
                                                'link': link,
                                                'source': 'Philkotse',
                                                'date': self._extract_date(item)
                                            })
                    except: continue
                
                if len(search_items) >= 10: break
            except: continue
            
        return search_items

    def _parse_price(self, price_str):
        digits = re.sub(r'[^\d]', '', str(price_str))
        return int(digits) if digits else 0

    def _extract_date(self, item):
        try:
            # Extract date from image URL (e.g., .../2026/01/27/...)
            img = item.select_one('img')
            if img:
                src = img.get('data-src') or img.get('src')
                if src:
                    match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', src)
                    if match:
                        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        except: pass
        return "N/A"

if __name__ == "__main__":
    s = PhilkotseScraper()
    res = s.search("Toyota", "Vios", "2023", fuzzy_search=True)
    print(f"Results: {len(res)}")
    for r in res[:3]: print(r)
