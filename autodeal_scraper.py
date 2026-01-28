import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
from fake_useragent import UserAgent
import time
import random

class AutoDealScraper:
    def __init__(self):
        self.base_url = "https://www.autodeal.com.ph"
        self.ua = UserAgent()

    def search(self, make, model, year, fuzzy_search=True):
        search_items = []
        
        # Normalize for URL slugs - AutoDeal often prefers Title-Case for makes
        make_slug = make.strip().replace(" ", "-").lower()
        model_slug = model.strip().replace(" ", "-").lower()
        
        # Strategy: Use the specific search filter URL pattern
        # /used-cars/search/used-car-status/toyota-make/vios-model/page-1?sort-by=relevance
        urls_to_try = [
            f"{self.base_url}/used-cars/search/used-car-status/{make_slug}-make/{model_slug}-model/page-1?sort-by=relevance",
            f"{self.base_url}/used-cars/search/{urllib.parse.quote(f'{make} {model} {year}')}"
        ]
        
        for url in urls_to_try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            }
            
            try:
                # 增加日誌以便在 UI 模式下記錄
                with open("scraper_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] AutoDeal: 嘗試抓取 {url}\n")
                
                time.sleep(random.uniform(1.0, 2.0))
                response = requests.get(url, headers=headers, timeout=20)
                
                with open("scraper_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] AutoDeal: 回傳狀態碼 {response.status_code}, 內容長度 {len(response.text)}\n")
                
                if response.status_code != 200: continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # AutoDeal selectors - Updated based on debug HTML
                listings = soup.select('article.card, .search-result-item, .card-car, .car-card')
                if not listings:
                    # Fallback to broad search if container classes vary
                    listings = soup.find_all(['article', 'div'], class_=re.compile(r'card|listing|search-item', re.I))

                for item in listings:
                    try:
                        # Skip decoration/header blocks
                        if item.get('id') == 'sort-bar' or 'stickyhead' in item.get('class', []): continue
                        
                        # Priority: h3 is usually the title in featured listings, h4 is the price
                        title_elem = item.find(['h3', 'h4', 'h2', 'a'], class_=re.compile(r'title|name|info', re.I)) or \
                                     item.find(['h3', 'h4', 'h2'])
                        
                        # Price detection: Search for P/PHP or Peso sign in various elements
                        price_elem = item.find('span', class_=re.compile(r'price|amount', re.I)) or \
                                     item.find(['h4', 'span', 'p'], string=re.compile(r'P|₱')) or \
                                     item.find(lambda tag: tag.name in ['h4', 'span', 'p'] and re.search(r'P|₱', tag.text))
                        
                        link_elem = item.find('a', class_=re.compile(r'title_click|details', re.I)) or \
                                    item.find('a', href=re.compile(r'/used-cars/')) or \
                                    item.find('a', href=True)

                        if title_elem and price_elem:
                            title = title_elem.get_text(strip=True)
                            price_text = price_elem if isinstance(price_elem, str) else price_elem.get_text(strip=True)
                            
                            # Clean up title if it contains price
                            if re.search(r'P|₱|\d{1,3},\d{3}', title) and not re.search(r'[a-zA-Z]', title):
                                # If title is just a price, and price_text is maybe a title, swap
                                if re.search(r'[a-zA-Z]', price_text):
                                    title, price_text = price_text, title
                            
                            if not re.search(r'\d', price_text): continue
                            
                            link = link_elem['href']
                            if not link.startswith('http'): link = self.base_url + link
                            
                            # Logic check - handle fuzzy search or specific year
                            match = False
                            title_lower = title.lower()
                            if model.lower() in title_lower:
                                if fuzzy_search:
                                    match = True
                                else:
                                    # Look for specific year or roughly adjacent years
                                    year_str = str(year)
                                    prev_year = str(int(year) - 1)
                                    next_year = str(int(year) + 1)
                                    if year_str in title or prev_year in title or next_year in title:
                                        match = True
                                
                            if match:
                                price = self._parse_price(price_text)
                                if price > 30000:
                                    if link not in [x['link'] for x in search_items]:
                                        search_items.append({
                                            'title': title,
                                            'price': price,
                                            'price_display': price_text.strip(),
                                            'link': link,
                                            'source': 'AutoDeal'
                                        })
                    except: continue
                
                if len(search_items) >= 5: break
            except Exception as e:
                print(f"AutoDeal error: {e}")
                continue
            
        return search_items

    def _parse_price(self, price_str):
        digits = re.sub(r'[^\d]', '', str(price_str))
        return int(digits) if digits else 0

if __name__ == "__main__":
    s = AutoDealScraper()
    res = s.search("Toyota", "Vios", "2023")
    print(f"AutoDeal: Found {len(res)} results")
    for r in res[:3]: print(r)
