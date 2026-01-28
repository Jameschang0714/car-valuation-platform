from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random
import re

class AutoDealScraper:
    def __init__(self):
        self.base_url = "https://www.autodeal.com.ph"

    def search(self, make, model, year, fuzzy_search=True):
        search_items = []
        
        # Normalize for URL slugs - AutoDeal often prefers Title-Case for makes
        make_slug = make.strip().replace(" ", "-").lower()
        model_slug = model.strip().replace(" ", "-").lower() if model else ""
        
        unique_urls = []
        use_generic_search = False

        if not model or " " in model:
             use_generic_search = True

        if use_generic_search:
             # Generic search: fallback to q=
             query = f"{make} {model}"
             encoded_query = urllib.parse.quote(query.strip())
             unique_urls.append(f"{self.base_url}/used-cars/search/{encoded_query}?sort-by=relevance")
             unique_urls.append(f"{self.base_url}/used-cars/search/{make_slug}%20{model_slug}")
        else:
            # Strict mode
            if year and str(year).isdigit():
                target_year = int(year)
                # Try specific range
                unique_urls.append(f"{self.base_url}/used-cars/search/used-car-status/{make_slug}-make/{model_slug}-model/{target_year}-year/page-1?sort-by=relevance")
            
            # General model search
            unique_urls.append(f"{self.base_url}/used-cars/search/used-car-status/{make_slug}-make/{model_slug}-model/page-1?sort-by=relevance")

            # Fallback to Make search if strict fails
            unique_urls.append(f"{self.base_url}/used-cars/search/{make_slug}%20{model_slug}")

        for url in unique_urls:
            try:
                # Log usage
                with open("scraper_debug.log", "a", encoding="utf-8") as f:
                     f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] AutoDeal: 嘗試抓取 {url}\n")
                
                # Use curl_cffi
                response = cffi_requests.get(
                    url, 
                    impersonate="chrome120", 
                    timeout=30
                )
                
                with open("scraper_debug.log", "a", encoding="utf-8") as f:
                     f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] AutoDeal: 回傳狀態碼 {response.status_code}, 內容長度 {len(response.text)}\n")

                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')
                listings = soup.select('.item-card, .vehicle-item, .search-item')
                
                for item in listings:
                    try:
                        title_elem = item.select_one('.vehicle-title, h2, h3, .title')
                        price_elem = item.select_one('.price, .vehicle-price, .amount')
                        link_elem = item.select_one('a')

                        if title_elem and price_elem:
                            title = title_elem.get_text(strip=True)
                            # --- FILTERING ---
                            is_relevant = False
                            if make.lower() in title.lower():
                                is_relevant = True
                            
                            # Loose keyword check
                            if not is_relevant and use_generic_search:
                                 query_parts = f"{make} {model}".split()
                                 q_keywords = [k.lower() for k in query_parts if len(k) > 2]
                                 if q_keywords and all(k in title.lower() for k in q_keywords):
                                      is_relevant = True
                            
                            if is_relevant:
                                 # If strictly searching for a model (e.g. Vios), check it
                                 # If generic (Wing Van), check if keywords present
                                 model_match = True
                                 if model:
                                      model_keywords = model.lower().split()
                                      if not all(k in title.lower() for k in model_keywords):
                                           model_match = False
                                 
                                 if model_match:
                                      if fuzzy_search:
                                           match = True
                                      else:
                                           # If specific year requested
                                           if year and str(year).isdigit():
                                                year_str = str(year)
                                                prev_year = str(int(year) - 1)
                                                next_year = str(int(year) + 1)
                                                if year_str in title or prev_year in title or next_year in title:
                                                     match = True
                                           else:
                                                match = True # No year requirement
                                 
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
