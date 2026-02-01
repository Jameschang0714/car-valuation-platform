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

    def _log(self, message):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] Facebook (Playwright): {message}\n"
        print(log_msg.strip())
        try:
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(log_msg)
        except: pass

    def search(self, make, model, year, fuzzy_search=True):
        results = []
        browser = None
        self._log(f"開始搜尋 {make} {model} {year}")
        try:
            with sync_playwright() as p:
                self._log("正在啟動 Chromium...")
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as b_err:
                    self._log(f"瀏覽器啟動失敗: {b_err}")
                    raise b_err

                self._log("建立瀏覽器上下文...")
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent=self.ua,
                    locale="en-PH"
                )
                page = context.new_page()
                
                query = f"{make} {model}"
                if year: query += f" {year}"
                url = f"{self.base_url}/marketplace/manila/search?query={query.replace(' ', '%20')}"
                
                self._log(f"正在前往 Marketplace: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                self._log("等待頁面載入並處理彈窗...")
                time.sleep(8)
                page.keyboard.press("Escape")
                
                self._log("開始提取連結...")
                all_links = page.query_selector_all('a')
                self._log(f"發現 {len(all_links)} 個連結，開始過濾...")
                processed_raw = []
                
                # ... (rest of the logic remains same, but I'll add a few more logs)
                for link in all_links:
                    try:
                        href = link.get_attribute('href') or ""
                        if "/marketplace/item/" in href or re.search(r'/\d{10,}/', href):
                            aria = link.get_attribute('aria-label')
                            inner = link.inner_text()
                            text = aria or inner or link.get_attribute('title')
                            if not text or len(text) < 5: continue
                            
                            # (價格提取代碼保持不變)
                            price_match = re.search(r'(?:₱|PHP|\$)\s*([\d,.]+)', text)
                            if price_match:
                                p_str = price_match.group(1).replace(",", "")
                                try:
                                    if '.' in p_str and p_str.count('.') == 1: p_val = int(float(p_str))
                                    else: p_val = int(p_str.replace('.', ''))
                                except: continue
                                
                                title = ""
                                if aria:
                                    parts = [p.strip() for p in re.split(r'·| - |\|', aria) if p.strip()]
                                    title = next((p for p in parts if not re.search(r'(?:₱|PHP|\$)\s*[\d,.]+', p)), "")
                                
                                if not title:
                                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                                    cands = [l for l in lines if not re.search(r'(?:₱|PHP|\$)\s*[\d,.]+', l)]
                                    title = next((l for l in cands if make.lower() in l.lower()), cands[0] if cands else "Vehicle")
                                
                                processed_raw.append({
                                    'title': title, 'price': p_val, 'price_display': f"₱{p_val:,}",
                                    'link': self.base_url + href if href.startswith('/') else href,
                                    'source': 'FB Marketplace', 'raw_text': text.lower()
                                })
                    except: continue

                self._log(f"初步獲取 {len(processed_raw)} 筆原始資料，開始精確過濾...")
                # ... (過濾邏輯)
                seen = set()
                make_lower = make.lower().strip()
                target_year = str(year) if year else ""
                
                for item in processed_raw:
                    t_lower, r_lower = item['title'].lower(), item['raw_text']
                    is_brand = (make_lower in t_lower) or (make_lower in r_lower)
                    if not is_brand and item['price'] > 300000:
                        if make_lower == "howo" and "sinotruk" in r_lower: is_brand = True
                        elif make_lower == "shacman" and ("shaanxi" in r_lower or "shac" in r_lower): is_brand = True
                    
                    if not is_brand: continue
                    
                    is_year = True
                    if target_year:
                        prev_year, next_year = str(int(year)-1), str(int(year)+1)
                        is_year = (target_year in r_lower) or (fuzzy_search and (prev_year in r_lower or next_year in r_lower))
                    
                    if is_year:
                        key = f"{item['title']}-{item['price']}"
                        if key not in seen:
                            results.append({
                                'title': item['title'], 'price': item['price'],
                                'price_display': item['price_display'], 'link': item['link'],
                                'source': item['source']
                            })
                            seen.add(key)
                
                self._log(f"搜尋完成，回傳 {len(results)} 筆有效結果")
                return results

        except Exception as e:
            self._log(f"發生錯誤: {e}")
            traceback.print_exc()
            return []
        finally:
            if browser:
                try: browser.close()
                except: pass

if __name__ == "__main__":
    s = FacebookScraper()
    print("Testing Facebook Scraper...")
    res = s.search("Toyota", "Vios", "2022")
    print(f"Results Found: {len(res)}")
    for r in res[:5]:
        print(f"- {r['title']}: {r['price_display']} ({r['link']})")
