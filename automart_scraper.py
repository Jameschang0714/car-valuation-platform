from curl_cffi import requests as cffi_requests
import urllib.parse
import time
import random
from datetime import datetime, timedelta

class AutomartScraper:
    def __init__(self):
        self.base_url = "https://automart.ph"
        self.api_url = "https://api.automart.ph/products"

    def search(self, make, model, year, fuzzy_search=True):
        results = []
        try:
            # Construct API Query
            # Removes "fields" restriction to fetch full object including price_order
            params = {
                "q": f"{make} {model} {year}",
                "limit": 20
            }
            query_url = f"{self.api_url}?{urllib.parse.urlencode(params)}"
            
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Automart (API): 查詢 {query_url}\n")
            
            # Use Chrome 120 impersonation to bypass Cloudflare/WAF
            response = cffi_requests.get(query_url, impersonate="chrome120", timeout=15)
            
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Automart: 狀態碼 {response.status_code}\n")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                for i, item in enumerate(items):
                    if i == 0: print(f"DEBUG Automart Keys: {item.keys()}")
                    try:
                        title = item.get('title')
                        # price_order is the reliable integer price field
                        price = item.get('price_order') 
                        slug = item.get('slug')
                        
                        if title and price and slug:
                            link = f"https://automart.ph/used-cars/{slug}"
                            
                            # Double check model match (API fuzzy search can be broad)
                            if model.lower() in title.lower():
                                # API v2: created_at missing, estimate from expired_at
                                date_str = 'N/A'
                                if 'expired_at' in item and item['expired_at']:
                                    try:
                                        # expired_at is typically created_at + 60 days
                                        exp_date = datetime.strptime(item['expired_at'].split(' ')[0], "%Y-%m-%d")
                                        est_created = exp_date - timedelta(days=60)
                                        date_str = est_created.strftime("%Y-%m-%d")
                                    except: pass

                                results.append({
                                    'title': title,
                                    'price': int(price),
                                    'price_display': f"₱{int(price):,}",
                                    'link': link,
                                    'source': 'Automart',
                                    'date': date_str
                                })
                    except Exception as e:
                        print(f"Automart item parse error: {e}")
                        continue
                        
        except Exception as e:
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Automart Error: {e}\n")
            try:
                print(f"Automart API Error: {e}")
            except:
                print("Automart API Error: (encoding error)")
            
        return results

    def _parse_price(self, price_str):
        # Unused in API mode but kept for compatibility if needed
        return 0
