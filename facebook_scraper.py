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
                # 改用更擬真的搜尋路徑
                # 先前往 Marketplace 首頁，再進行搜尋
                url = f"{self.base_url}/marketplace/search/?query={query.replace(' ', '%20')}"
                
                self._log(f"正在前往 Marketplace: {url}")
                # 增加更長的隨機延遲並使用隨機的桌面級 User-Agent
                page.goto(url, wait_until="networkidle", timeout=60000)
                
                self._log("等待頁面加載並嘗試對抗登入牆...")
                time.sleep(random.uniform(5, 10))
                
                # 再次模擬真人嘗試關閉彈窗
                page.keyboard.press("Escape")
                
                self._log("偵核頁面標題與內容長度...")
                title = page.title()
                content_len = len(page.content())
                self._log(f"標題: {title}, 內容長度: {content_len}")

                if "Log In" in title or "登入" in title:
                    self._log("警告：遇到了登入牆，嘗試進行滾動以觸發延遲加載")
                
                page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
                time.sleep(3)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(3)

                self._log("開始提取所有具備商品特徵的連結...")
                all_links = page.query_selector_all('a[href*="/marketplace/item/"]')
                # 如果找不到具備明顯特徵的，擴大搜尋範圍
                if not all_links:
                    self._log("未發現標準 item 連結，嘗試獲取所有連結並正則匹配...")
                    all_links = page.query_selector_all('a')
                
                self._log(f"初步發現 {len(all_links)} 個潛在連結，開始深度解析...")
                processed_raw = []
                
                for link in all_links:
                    try:
                        href = link.get_attribute('href') or ""
                        # 檢查網址是否包含商品特徵：/marketplace/item/ 或一串純數字（ID）
                        is_item = "/marketplace/item/" in href or (re.search(r'/\d{10,}/', href) and "marketplace" in href)
                        
                        if is_item:
                            aria = link.get_attribute('aria-label')
                            inner = link.inner_text()
                            text = aria or inner or link.get_attribute('title')
                            
                            # 強化：如果 text 很短，嘗試找鄰近的文字（FB 結構常變動）
                            if not text or len(text) < 10:
                                # 嘗試獲取父層或子層文字
                                text = link.evaluate("el => el.innerText")
                            
                            if not text or len(text) < 5: continue
                            
                            # (後續過濾邏輯保持不變)
                            price_match = re.search(r'(?:₱|PHP|\$)\s*([\d,.]+)', text)
                            if price_match:
                                p_str = price_match.group(1).replace(",", "")
                                try:
                                    if '.' in p_str and p_str.count('.') == 1: p_val = int(float(p_str))
                                    else: p_val = int(p_str.replace('.', ''))
                                except: continue
                                
                                # 匯率轉換
                                if '$' in price_match.group(0) and p_val < 50000: p_val *= 56
                                if p_val < 15000: continue
                                
                                item_title = ""
                                if aria:
                                    parts = [p.strip() for p in re.split(r'·| - |\|', aria) if p.strip()]
                                    item_title = next((p for p in parts if not re.search(r'(?:₱|PHP|\$)\s*[\d,.]+', p)), "")
                                
                                if not item_title:
                                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                                    cands = [l for l in lines if not re.search(r'(?:₱|PHP|\$)\s*[\d,.]+', l)]
                                    item_title = next((l for l in cands if make.lower() in l.lower()), cands[0] if cands else "Vehicle")
                                
                                # 補上 facebook.com 前綴
                                full_link = href
                                if href.startswith('/'): full_link = self.base_url + href
                                elif "facebook.com" not in href: full_link = self.base_url + "/marketplace/item/" + href.split('/')[-1]

                                processed_raw.append({
                                    'title': item_title, 'price': p_val, 'price_display': f"₱{p_val:,}",
                                    'link': full_link, 'source': 'FB Marketplace', 'raw_text': text.lower()
                                })
                    except: continue

                self._log(f"初步獲取 {len(processed_raw)} 筆符合價格特徵的原始資料，開始品牌/年份過濾...")
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
