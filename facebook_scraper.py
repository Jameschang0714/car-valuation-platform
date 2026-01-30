from playwright.sync_api import sync_playwright
import re
import time
import random
import traceback
import sys

class FacebookScraper:
    def __init__(self):
        self.base_url = "https://www.facebook.com"
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

    def search(self, make, model, year, fuzzy_search=True):
        """
        Synchronous search using Playwright sync_api.
        Enhanced title extraction and reliable brand filtering.
        """
        results = []
        browser = None
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent=self.ua,
                    locale="en-PH"
                )
                page = context.new_page()
                
                query = f"{make} {model}"
                if year: query += f" {year}"
                url = f"{self.base_url}/marketplace/manila/search?query={query.replace(' ', '%20')}"
                
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(6)
                
                # Dismiss initial dialogs
                try: page.keyboard.press("Escape")
                except: pass
                
                # Minimal scrolling to trigger loading
                for _ in range(2):
                    page.mouse.wheel(0, 1000)
                    time.sleep(2)
                
                # Extract all potential links
                all_links = page.query_selector_all('a')
                processed_raw = []
                
                for link in all_links:
                    try:
                        href = link.get_attribute('href') or ""
                        if "/marketplace/item/" in href or re.search(r'/\d{10,}/', href):
                            aria = link.get_attribute('aria-label')
                            inner = link.inner_text()
                            text = aria or inner or link.get_attribute('title')
                            
                            if not text or len(text) < 5: continue
                            
                            price_match = re.search(r'(?:₱|PHP|\$)\s*([\d,.]+)', text)
                            if price_match:
                                p_str = price_match.group(1).replace(",", "")
                                p_val = int(float(p_str)) if '.' in p_str and p_str.count('.') == 1 else int(p_str.replace('.', ''))
                                
                                if '$' in price_match.group(0) and p_val < 50000: p_val *= 56
                                if p_val < 15000: continue
                                
                                # Title Extraction from ARIA or lines
                                title = ""
                                if aria:
                                    parts = [p.strip() for p in re.split(r'·| - |\|', aria) if p.strip()]
                                    title = next((p for p in parts if not re.search(r'(?:₱|PHP|\$)\s*[\d,.]+', p)), "")
                                
                                if not title:
                                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                                    cands = [l for l in lines if not re.search(r'(?:₱|PHP|\$)\s*[\d,.]+', l)]
                                    title = next((l for l in cands if make.lower() in l.lower()), cands[0] if cands else "Vehicle")
                                
                                processed_raw.append({
                                    'title': title,
                                    'price': p_val,
                                    'price_display': f"₱{p_val:,}",
                                    'link': self.base_url + href if href.startswith('/') else href,
                                    'source': 'FB Marketplace',
                                    'raw_text': text.lower()
                                })
                    except: continue

                # Filtering Logic
                make_lower = make.lower().strip()
                target_year = str(year) if year else ""
                seen = set()
                
                for item in processed_raw:
                    t_lower = item['title'].lower()
                    r_lower = item['raw_text']
                    
                    # 基礎品牌匹配
                    is_brand = (make_lower in t_lower) or (make_lower in r_lower)
                    
                    # 針對卡車品牌子母關聯的特殊放寬 (例如搜尋 HOWO 應包含 Sinotruk)
                    if not is_brand and item['price'] > 500000:
                        if make_lower == "howo" and "sinotruk" in r_lower:
                            is_brand = True
                        elif make_lower == "shacman" and ("shaanxi" in r_lower or "shac" in r_lower):
                            is_brand = True
                            
                    if not is_brand: continue
                    
                    is_year = True
                    if target_year:
                        is_year = (target_year in r_lower) or (fuzzy_search and (str(int(year)-1) in r_lower or str(int(year)+1) in r_lower))
                    
                    if is_year:
                        key = f"{item['title']}-{item['price']}"
                        if key not in seen:
                            results.append({
                                'title': item['title'],
                                'price': item['price'],
                                'price_display': item['price_display'],
                                'link': item['link'],
                                'source': item['source']
                            })
                            seen.add(key)
                
                return results

        except Exception as e:
            traceback.print_exc()
            return []
        finally:
            if browser:
                try: browser.close()
                except: pass

if __name__ == "__main__":
    s = FacebookScraper()
    print("Testing HOWO wing van...")
    res = s.search("HOWO", "wing van", "")
    print(f"Results: {len(res)}")
    for r in res[:5]:
        print(f"- {r['title']}: {r['price_display']}")
