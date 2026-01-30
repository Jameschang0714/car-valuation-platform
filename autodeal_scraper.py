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
                
                # Implement Robust Session Logic (v3.3.6)
                max_retries = 3
                browser_types = ["chrome110", "edge101", "safari15_5"]
                
                # 1. Pick ONE fingerprint for the entire session
                chosen_browser = random.choice(browser_types)
                
                # 2. Initialize Session
                s = cffi_requests.Session(impersonate=chosen_browser)
                
                # 3. WARM-UP: Visit Homepage to get initial cookies/clearance
                try:
                    with open("scraper_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] AutoDeal: 暖身訪問首頁 (Browser: {chosen_browser})...\n")
                    
                    s.get(
                        "https://www.autodeal.com.ph/",
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36", # Fallback UA
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                            "Accept-Language": "en-US,en;q=0.9",
                        },
                        timeout=15
                    )
                    time.sleep(random.uniform(2, 4))
                except Exception as e:
                    with open("scraper_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"AutoDeal Warmup Failed: {e}\n")

                # 4. TARGET REQUEST
                response = None
                for attempt in range(max_retries):
                    # Random delay before request
                    time.sleep(random.uniform(2, 5))
                    
                    headers = {
                        "Referer": "https://www.autodeal.com.ph/used-cars",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Authority": "www.autodeal.com.ph"
                    }

                    # Use session (fingerprint is already set)
                    response = s.get(
                        url, 
                        timeout=30,
                        headers=headers
                    )
                    
                    with open("scraper_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] AutoDeal (Attempt {attempt+1}): 回傳狀態碼 {response.status_code}\n")

                    if response.status_code == 200:
                        break
                    elif response.status_code == 202:
                        # 202 Accepted = Challenge running, wait and retry
                        time.sleep(5) 
                        continue
                    else:
                        break 
                
                if not response or response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')
                listings = soup.select('#results-view article.card')
                
                if not listings:
                    listings = soup.select('.item-card, .vehicle-item, .search-item')
                
                for item in listings:
                    try:
                        title_elem = item.select_one('h3') or item.select_one('.vehicle-title, .title')
                        price_elem = item.select_one('h4') or item.select_one('.price, .vehicle-price, .amount')
                        link_elem = item.select_one('a')
                        
                        link = ""
                        if link_elem and link_elem.has_attr('href'):
                            link = link_elem['href']
                            if not link.startswith('http'):
                                link = self.base_url + link

                        if title_elem and price_elem:
                            title = title_elem.get_text(strip=True)
                            price_text = price_elem.get_text(strip=True)
                            
                            is_relevant = False
                            if make.lower() in title.lower():
                                is_relevant = True
                            
                            if not is_relevant and use_generic_search:
                                query_parts = f"{make} {model}".split()
                                q_keywords = [k.lower() for k in query_parts if len(k) > 2]
                                if q_keywords and all(k in title.lower() for k in q_keywords):
                                    is_relevant = True
                            
                            if is_relevant:
                                model_match = True
                                if model:
                                    model_keywords = model.lower().split()
                                    if not all(k in title.lower() for k in model_keywords):
                                        model_match = False
                                
                                if model_match:
                                    match = True
                                    if year and str(year).isdigit():
                                        year_str = str(year)
                                        if fuzzy_search:
                                            prev_year = str(int(year) - 1)
                                            next_year = str(int(year) + 1)
                                            if year_str not in title and prev_year not in title and next_year not in title:
                                                match = False
                                        else:
                                            if year_str not in title:
                                                match = False
                                    
                                    if match:
                                        price = self._parse_price(price_text)
                                        if price > 30000:
                                            mileage_text = "N/A"
                                            spans = item.find_all('span')
                                            for s_tag in spans:
                                                t_str = s_tag.get_text(strip=True)
                                                if 'km' in t_str.lower():
                                                    mileage_text = t_str
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
