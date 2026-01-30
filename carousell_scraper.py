import requests
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
import json
import re
import urllib.parse
from fake_useragent import UserAgent
import time
import random

class CarousellScraper:
    def __init__(self):
        self.base_url = "https://www.carousell.ph"
        self.ua = UserAgent()

    def search(self, make, model, year, fuzzy_search=True):
        query = f"{make} {model} {year}"
        encoded_query = urllib.parse.quote(query)
        url = f"{self.base_url}/search/{encoded_query}/?category_id=32&sort_by=3"
        
        # Realistic Modern Browser Headers
        # Note: curl_cffi impersonate handles most headers. Overriding them manually can break the fingerprint.
        # We only set Referer (sometimes helpful) but let impersonate manage User-Agent and others.
        
        try:
            # Power-up: Robust Session Logic (v3.3.6)
            browser_types = ["chrome110", "edge101", "safari15_5"]
            chosen_browser = random.choice(browser_types)
            
            # 1. Init Session with fixed fingerprint
            s = cffi_requests.Session(impersonate=chosen_browser)
            
            # 2. WARM-UP
            try:
                with open("scraper_debug.log", "a", encoding="utf-8") as f:
                     f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Carousell (CFFI): 暖身訪問首頁 (Browser: {chosen_browser})...\n")
                
                s.get(
                    "https://www.carousell.ph/",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                    timeout=15
                )
                time.sleep(random.uniform(2, 4))
            except: pass

            url = f"{self.base_url}/search/{encoded_query}/?category_id=32&sort_by=3"
            
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Carousell: 嘗試抓取 {url}\n")
            
            headers = {
                "Referer": "https://www.carousell.ph/",
                "Origin": "https://www.carousell.ph",
                "Accept-Language": "en-US,en;q=0.9"
            }

            # 3. Request
            response = s.get(
                url, 
                timeout=30,
                verify=False,
                headers=headers
            )
            
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Carousell: 回傳狀態碼 {response.status_code}, 內容長度 {len(response.text)}\n")
            
            if response.status_code != 200:
                return []
            
            # Save HTML for debugging
            with open("carousell_debug.html", "w", encoding="utf-8") as f:
                f.write(response.text)

            soup = BeautifulSoup(response.text, 'html.parser')
            results = []

            # JSON extraction (__NEXT_DATA__)
            script_tag = soup.find('script', id='__NEXT_DATA__')
            if script_tag:
                try:
                    data = json.loads(script_tag.string)
                    results = self._extract_listings_from_json(data)
                    if results: return results
                except: pass

            # Fallback CSS Selectors (Current Carousell Web)
            items = soup.select('div[data-testid^="listing-card"]')

            for item in items:
                try:
                    # 1. Extract Link (Product link starts with /p/)
                    link_elem = item.find('a', href=re.compile(r'^/p/'))
                    if not link_elem: continue
                    
                    raw_link = link_elem['href']
                    link = self.base_url + raw_link if not raw_link.startswith('http') else raw_link

                    # 2. Extract Price (Look for p tag with title="PHP ...")
                    price_elem = item.find('p', title=re.compile(r'PHP', re.I))
                    if not price_elem:
                        # Fallback: look for text matching price pattern
                        price_elem = item.find(string=re.compile(r'PHP\s|₱', re.I))
                    
                    price = 0
                    price_text = "0"
                    if price_elem:
                        # Extract text safely
                        txt = None
                        # Check if it has 'get' (Tag) and title attr
                        if hasattr(price_elem, 'get'):
                            txt = price_elem.get('title')
                        
                        # If no title, get text content
                        if not txt and hasattr(price_elem, 'get_text'):
                             txt = price_elem.get_text(strip=True)
                        
                        # Fallback for NavigableString
                        if not txt:
                             txt = str(price_elem)
                        
                        price = self._parse_price(txt)
                        price_text = txt

                    # 3. Extract Title
                    # Strategy: Find p tag with style="--max-line:2" OR exclude seller/price
                    title_elem = item.find('p', style=re.compile(r'--max-line:2'))
                    
                    if not title_elem:
                         # Fallback: Find all p tags, exclude known others
                         ps = item.find_all('p')
                         candidates = []
                         for p in ps:
                             # Exclude seller
                             if p.get('data-testid') == 'listing-card-text-seller-name': continue
                             # Exclude price (if it has title=PHP)
                             if p.get('title') and 'PHP' in p.get('title'): continue
                             # Exclude short labels (Time, Condition)
                             text = p.get_text(strip=True)
                             if len(text) < 4: continue 
                             candidates.append(p)
                         
                         if candidates:
                             # Pick the longest text as likely title
                             title_elem = max(candidates, key=lambda x: len(x.get_text()))

                    # 4. Extract Date (Regex fallback)
                    date_str = "N/A"
                    # Try to find a date pattern in any <p> tag
                    all_ps = item.find_all('p')
                    for p in all_ps:
                        text = p.get_text(strip=True)
                        # Regex for "8 days ago", "yesterday", "2 hours ago", "just now", "30+ days ago"
                        if re.search(r'(\d+\+?\s+(minute|hour|day|week|month|year)s?\s+ago|yesterday|today|just now)', text, re.IGNORECASE):
                            date_str = text
                            break

                    if title_elem and price > 20000:
                        title = title_elem.get_text(strip=True)
                        results.append({
                            'title': title,
                            'price': price,
                            'price_display': price_text,
                            'link': link,
                            'source': 'Carousell',
                            'date': date_str
                        })
                        
                        # Apply Fuzzy/Strict Year Filter
                        if year and str(year).isdigit():
                            target_year = str(year)
                            is_match = False
                            if target_year in title:
                                is_match = True
                            elif fuzzy_search:
                                # If fuzzy, check adjacent years
                                prev = str(int(year)-1)
                                next_y = str(int(year)+1)
                                if prev in title or next_y in title:
                                    is_match = True
                            
                            if not is_match:
                                results.pop() # Remove the last added item
                except Exception as e:
                     # print(f"Item parse error: {e}")
                     continue
            
            return results
        except:
            return []

    def _extract_listings_from_json(self, data):
        listings = []
        try:
            # Flattened traversal for searchResults
            def find_key(obj, target):
                if isinstance(obj, dict):
                    if target in obj: return obj[target]
                    for v in obj.values():
                        res = find_key(v, target)
                        if res: return res
                elif isinstance(obj, list):
                    for v in obj:
                        res = find_key(v, target)
                        if res: return res
                return None

            sr = find_key(data, 'searchResults') or find_key(data, 'results')
            if sr:
                for item in sr:
                    # Support multiple JSON variants
                    lc = item.get('listingCard') or item
                    if len(listings) == 0: print(f"DEBUG Carousell LC Keys: {lc.keys()}")
                    title = lc.get('title')
                    price_text = lc.get('price')
                    listing_id = lc.get('id') or lc.get('listingId')
                    
                    if title and price_text:
                        price = self._parse_price(price_text)
                        if price > 20000:
                            # Fix Link: Use direct product ID link
                            link = f"{self.base_url}/p/{listing_id}" if listing_id else self.base_url
                            
                            # Extract Date
                            date_str = "N/A"
                            if 'timeCreated' in lc:
                                try:
                                    # Convert timestamp to YYYY-MM-DD
                                    # Carousell timestamp is usually standard ISO or similar
                                    # But sometimes it's just 'timeAgo' string
                                    date_str = lc.get('timeCreated') # Expecting ISO string or similar
                                    # If it's a raw timestamp integer/string?
                                    pass 
                                except: pass
                            elif 'timeAgo' in lc:
                                date_str = lc.get('timeAgo')

                            listings.append({
                                'title': title,
                                'price': price,
                                'price_display': price_text,
                                'link': link,
                                'source': 'Carousell',
                                'date': date_str
                            })
        except: pass
        return listings

    def _parse_price(self, price_str):
        digits = re.sub(r'[^\d]', '', str(price_str))
        return int(digits) if digits else 0

if __name__ == "__main__":
    s = CarousellScraper()
    res = s.search("Toyota", "Vios", "2023")
    print(f"Carousell Final Test: {len(res)} results")
