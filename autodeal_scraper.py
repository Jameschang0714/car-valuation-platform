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
        
        # Normalize for URL slugs
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
                unique_urls.append(f"{self.base_url}/used-cars/search/used-car-status/{make_slug}-make/{model_slug}-model/{target_year}-year/page-1?sort-by=relevance")
            
            # General model search
            unique_urls.append(f"{self.base_url}/used-cars/search/used-car-status/{make_slug}-make/{model_slug}-model/page-1?sort-by=relevance")

            # Fallback
            unique_urls.append(f"{self.base_url}/used-cars/search/{make_slug}%20{model_slug}")

        for url in unique_urls:
            try:
                # Log usage
                with open("scraper_debug.log", "a", encoding="utf-8") as f:
                     f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] AutoDeal: 嘗試抓取 {url}\n")
                
                # Implement Retry Logic with Session for Cookie Persistence
                max_retries = 3
                browser_types = ["chrome110", "edge101", "safari15_5"]
                
                # Use a session to persist cookies (vital for 202 challenges)
                s = cffi_requests.Session()
                
                for attempt in range(max_retries):
                    # Randomize browser for the session
                    impersonate_browser = random.choice(browser_types)
                    
                    # Random delay before request
                    time.sleep(random.uniform(1, 4))
                    
                    headers = {
                        "Referer": "https://www.autodeal.com.ph/used-cars",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Authority": "www.autodeal.com.ph"
                    }

                    # Use session
                    response = s.get(
                        url, 
                        impersonate=impersonate_browser, 
                        timeout=30,
                        headers=headers
                    )
                    
                    with open("scraper_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] AutoDeal (Attempt {attempt+1}): 回傳狀態碼 {response.status_code} (Browser: {impersonate_browser})\n")

                    if response.status_code == 200:
                        break
                    elif response.status_code == 202:
                        # 202 Accepted = Challenge running, wait and retry
                        # The session 's' will hold the new cookies
                        time.sleep(3) # Wait longer for challenge to clear
                        continue
                    else:
                        break 

                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')
                
                # NEW SELECTOR STRATEGY 2025-01-30
                # Main listing container seems to be #results-view containing <article class="card">
                listings = soup.select('#results-view article.card')
                
                if not listings:
                    # Fallback for old layout just in case
                    listings = soup.select('.item-card, .vehicle-item, .search-item')
                
                for item in listings:
                    try:
                        # Title is usually in h3 tag now
                        title_elem = item.select_one('h3')
                        if not title_elem:
                            title_elem = item.select_one('.vehicle-title, .title')
                            
                        # Price is in h4 tag
                        price_elem = item.select_one('h4')
                        if not price_elem:
                            price_elem = item.select_one('.price, .vehicle-price, .amount')
                            
                        # Link is usually within the first A tag inside the title/image container
                        link_elem = item.select_one('a')
                        link = ""
                        if link_elem and link_elem.has_attr('href'):
                            link = link_elem['href']
                            if not link.startswith('http'):
                                link = self.base_url + link

                        if title_elem and price_elem:
                            title = title_elem.get_text(strip=True)
                            price_text = price_elem.get_text(strip=True)
                            
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
                                           match = True # Default to true as year might not be in title
                                           if year and str(year).isdigit():
                                                year_str = str(year)
                                                prev_year = str(int(year) - 1)
                                                next_year = str(int(year) + 1)
                                                if year_str in title:
                                                     match = True
                                                elif prev_year in title or next_year in title:
                                                     match = True
                                                else:
                                                     match = False
                                 
                            if match:
                                price = self._parse_price(price_text)
                                if price > 30000:
                                    # Extract Mileage if available
                                    mileage_text = "N/A"
                                    # Mileage is often in spans like <span>31,800 Km</span>
                                    spans = item.find_all('span')
                                    for s in spans:
                                        t = s.get_text(strip=True)
                                        if 'km' in t.lower():
                                            mileage_text = t
                                            break
                                            
                                    entry = {
                                            'title': title,
                                            'price': price,
                                            'price_display': price_text.strip(),
                                            'link': link,
                                            'source': 'AutoDeal',
                                            'mileage': mileage_text
                                        }

                                    if entry['link'] not in [x['link'] for x in search_items]:
                                        search_items.append(entry)
                                        
                    except Exception as e: 
                        # print(f"Item parse error: {e}")
                        continue
                
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
