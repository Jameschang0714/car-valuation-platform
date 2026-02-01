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
        self._log(f"開始搜尋 {make} {model} {year} (Stealth 桌面模式)")
        try:
            with sync_playwright() as p:
                self._log("正在啟動 Stealth Chromium...")
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as b_err:
                    self._log(f"瀏覽器啟動失敗: {b_err}")
                    raise b_err

                # 強化隱身標頭
                stealth_context = {
                    'viewport': {'width': 1366, 'height': 768},
                    'user_agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    'locale': "en-PH",
                    'extra_http_headers': {
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'en-PH,en-US;q=0.9,en;q=0.8',
                        'Referer': 'https://www.facebook.com/',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'same-origin',
                        'Sec-Fetch-User': '?1',
                        'Upgrade-Insecure-Requests': '1'
                    }
                }
                
                context = browser.new_context(**stealth_context)
                page = context.new_page()
                
                query = f"{make} {model}"
                if year: query += f" {year}"
                
                # 使用馬尼拉特定的地區 ID (108155919213134)
                # 這種方式通常比全局 /marketplace/search/ 更容易繞過登入牆
                url = f"https://www.facebook.com/marketplace/108155919213134/search?query={query.replace(' ', '%20')}"
                
                self._log(f"正在前往馬尼拉地區 Marketplace: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                self._log("執行頁面解析與抗阻斷延遲...")
                time.sleep(random.uniform(6, 10))
                
                title = page.title()
                content_len = len(page.content())
                self._log(f"頁面載入完成。標題: {title}, 長度: {content_len}")

                if "Log In" in title or "登入" in title:
                    self._log("偵測到登入牆，嘗試發送逃脫鍵並觸發滾動...")
                    page.keyboard.press("Escape")
                    time.sleep(2)
                
                # 滾動以加載
                for i in range(3):
                    page.evaluate(f"window.scrollBy(0, 800)")
                    time.sleep(2)

                self._log("開始深度提取商品特徵連結...")
                # 針對 FB 新版桌面版結構，尋找所有 A 連結
                all_links = page.query_selector_all('a')
                self._log(f"發現 {len(all_links)} 個原始連結，執行特徵匹配...")
                
                processed_raw = []
                for link in all_links:
                    try:
                        href = link.get_attribute('href') or ""
                        # FB 桌面版商品連結特徵
                        if "/marketplace/item/" in href:
                            # 獲取完整文字塊
                            text = link.inner_text() or link.get_attribute('aria-label') or ""
                            
                            if not text or len(text) < 10: continue
                            
                            price_match = re.search(r'(?:₱|PHP|\$)\s*([\d,.]+)', text)
                            if price_match:
                                p_str = price_match.group(1).replace(",", "")
                                try:
                                    p_val = int(float(p_str)) if '.' in p_str else int(p_str.replace('.', ''))
                                except: continue
                                
                                # 匯率與基本過濾
                                if '$' in price_match.group(0) and p_val < 50000: p_val *= 56
                                if p_val < 15000: continue
                                
                                # 標題提取
                                lines = [l.strip() for l in text.split('\n') if l.strip()]
                                item_title = next((l for l in lines if not re.search(r'(?:₱|PHP|\$|·)', l)), "Vehicle")
                                
                                full_link = self.base_url + href if href.startswith('/') else href
                                
                                processed_raw.append({
                                    'title': item_title, 'price': p_val, 'price_display': f"₱{p_val:,}",
                                    'link': full_link, 'source': 'FB Marketplace', 'raw_text': text.lower()
                                })
                    except: continue

                self._log(f"成功提取 {len(processed_raw)} 筆潛在商品，進入精確過濾...")
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
