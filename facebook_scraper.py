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
        self._log(f"開始搜尋 {make} {model} {year} (mbasic 模式)")
        try:
            with sync_playwright() as p:
                self._log("正在啟動 Chromium...")
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as b_err:
                    self._log(f"瀏覽器啟動失敗: {b_err}")
                    raise b_err

                # mbasic 模式不需要太複雜的 context
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
                    locale="en-PH"
                )
                page = context.new_page()
                
                query = f"{make} {model}"
                if year: query += f" {year}"
                
                # mbasic 的搜尋 URL
                url = f"https://mbasic.facebook.com/marketplace/search/?query={query.replace(' ', '%20')}"
                
                self._log(f"正在前往 mbasic Marketplace: {url}")
                # mbasic 頁面非常輕量，通常不需要等待 networkidle
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # 增加穩定的處理延遲
                time.sleep(random.uniform(4, 7))
                
                title = page.title()
                content_len = len(page.content())
                self._log(f"mbasic 頁面載入。標題: {title}, 長度: {content_len}")

                # mbasic 通常不會有逃脫鍵需求，但為了保險保留
                if "Log In" in title or "登入" in title:
                    self._log("警告：mbasic 仍顯示登入提示，嘗試繼續解析內容...")

                self._log("開始提取 mbasic 連結...")
                # mbasic 的連結通常很直接
                all_links = page.query_selector_all('a[href*="/marketplace/item/"]')
                # 如果找不到，嘗試正則匹配所有 a
                if not all_links:
                    all_links = [a for a in page.query_selector_all('a') if "/marketplace/item/" in (a.get_attribute('href') or "")]
                
                self._log(f"發現 {len(all_links)} 個包含 marketplace 的連結，啟動 mbasic 解析器...")
                
                processed_raw = []
                for link in all_links:
                    try:
                        href = link.get_attribute('href') or ""
                        # mbasic 的文字通常就在 <a> 標籤內或其父節點
                        # 我們向上找一層或拿自己的 inner_text
                        text = link.inner_text() or ""
                        if not text:
                            # 嘗試獲取父級文字（mbasic 結構常將圖片與文字分開在 div 內）
                            text = link.evaluate("el => el.parentElement.innerText")
                        
                        if not text or len(text) < 5: continue
                        
                        # 診斷日誌
                        if len(processed_raw) < 2:
                            self._log(f"mbasic 樣本輸出: {text.replace('\n', ' | ')[:100]}...")

                        # 價格解析
                        price_match = re.search(r'(?:₱|PHP|\$)\s*([\d,.]+)', text)
                        if price_match:
                            p_str = price_match.group(1).replace(",", "")
                            try:
                                p_val = int(float(p_str)) if '.' in p_str else int(p_str.replace('.', ''))
                            except: continue
                            
                            if '$' in price_match.group(0) and p_val < 50000: p_val *= 56
                            if p_val < 15000: continue
                            
                            lines = [l.strip() for l in text.split('\n') if l.strip()]
                            # mbasic 的標題通常是第一行文字（排除價格行）
                            item_title = next((l for l in lines if not re.search(r'(?:₱|PHP|\$|·)', l)), "Vehicle")
                            
                            # 轉換為標準 FB 網址
                            item_id = ""
                            id_match = re.search(r'/item/(\d+)', href)
                            if id_match:
                                item_id = id_match.group(1)
                                full_link = f"https://www.facebook.com/marketplace/item/{item_id}/"
                            else:
                                full_link = "https://www.facebook.com" + href if href.startswith('/') else href

                            processed_raw.append({
                                'title': item_title, 'price': p_val, 'price_display': f"₱{p_val:,}",
                                'link': full_link, 'source': 'FB Marketplace', 'raw_text': text.lower()
                            })
                    except: continue

                self._log(f"mbasic 成功獲取 {len(processed_raw)} 筆原始商品資料")
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
