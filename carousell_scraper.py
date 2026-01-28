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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
            "Referer": "https://www.google.com/"
        }
        
        try:
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Carousell (CFFI): 嘗試抓取 {url}\n")
            
            # Use curl_cffi to bypass TLS fingerprinting
            # timeout matches standard requests usage
            response = cffi_requests.get(url, impersonate="chrome120", timeout=30)
            
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Carousell: 回傳狀態碼 {response.status_code}, 內容長度 {len(response.text)}\n")
            
            if response.status_code != 200:
                return []

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
            items = soup.select('div[data-testid^="listing-card"], div.M-') # Carousell matches many M- classes
            if not items:
                # Last ditch: all links that look like products
                items = soup.select('a[href^="/p/"]')

            for item in items:
                try:
                    # Generic search for prices and titles within the block
                    title = item.find(string=re.compile(f"{make}|{model}", re.I))
                    price_elem = item.find(string=re.compile(r'₱|\d{3,},?\d{3}'))
                    # Link extraction priority: /p/ link -> any link
                    link_elem = item.find('a', href=re.compile(r'/p/')) or \
                                (item if item.name == 'a' else item.find('a', href=True))

                    if title and price_elem and link_elem:
                        price_text = price_elem.strip()
                        price = self._parse_price(price_text)
                        
                        raw_link = link_elem['href']
                        # Ensure we don't capture seller profile links (/u/)
                        if '/u/' in raw_link and not '/p/' in raw_link:
                            # Try finding another link in the same item that has /p/
                            alt_link = item.find('a', href=re.compile(r'/p/'))
                            if alt_link: raw_link = alt_link['href']
                        
                        link = self.base_url + raw_link if not raw_link.startswith('http') else raw_link

                        if price > 20000:
                            results.append({
                                'title': title.strip(),
                                'price': price,
                                'price_display': price_text,
                                'link': link,
                                'source': 'Carousell',
                                'date': 'N/A'
                            })
                except: continue
            
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
