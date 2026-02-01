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
        self._log(f"開始搜尋 {make} {model} {year} (mbasic Pro 模式)")
        try:
            with sync_playwright() as p:
                self._log("正在啟動 Chromium...")
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as b_err:
                    self._log(f"瀏覽器啟動失敗: {b_err}")
                    raise b_err

                # 使用更擬真的上下文
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                    locale="en-PH"
                )
                
                # 預留 Cookie 注入位置 (未來可由此填入使用者提供的 Session)
                # context.add_cookies([...])
                
                page = context.new_page()
                
                query = f"{make} {model}"
                if year: query += f" {year}"
                
                # 改用 mbasic 搜尋路徑
                url = f"https://mbasic.facebook.com/marketplace/search/?query={query.replace(' ', '%20')}"
                
                self._log(f"前往 mbasic: {url}")
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                time.sleep(random.uniform(5, 8))
                
                title = page.title()
                self._log(f"頁面載入。標題: {title}")

                # 如果遇到登入牆，嘗試點擊「Not Now」或類似按鈕（如果有的話）
                if "Log In" in title or "登入" in title:
                    self._log("偵測到登入牆，嘗試在 mbasic 尋找繞過路徑...")
                
                # mbasic 結構解析強化
                self._log("提取 mbasic 元素...")
                # mbasic 的 Marketplace 商品通常包裹在特定的 table 或 div 中
                # 我們尋找包含 "/marketplace/item/" 的所有連結
                elements = page.query_selector_all('a[href*="/marketplace/item/"]')
                
                if not elements:
                    self._log("未發現直接商品連結，嘗試寬鬆匹配...")
                    elements = [a for a in page.query_selector_all('a') if "/marketplace/item/" in (a.get_attribute('href') or "")]

                self._log(f"發現 {len(elements)} 個商品候選點，開始深度提取...")
                
                processed_raw = []
                for el in elements:
                    try:
                        href = el.get_attribute('href') or ""
                        # mbasic 價格與標題通常在連結標籤內，或緊鄰的 div 內
                        text = el.inner_text() or ""
                        
                        # 如果 text 只有價格，標題可能在父層
                        parent_text = el.evaluate("node => node.parentElement ? node.parentElement.innerText : ''")
                        full_text = text + " " + parent_text
                        
                        if not full_text or len(full_text) < 5: continue
                        
                        # 解析價格
                        price_match = re.search(r'(?:₱|PHP|\$)\s*([\d,.]+)', full_text)
                        if price_match:
                            p_str = price_match.group(1).replace(",", "")
                            try:
                                p_val = int(float(p_str)) if '.' in p_str else int(p_str.replace('.', ''))
                            except: continue
                            
                            if '$' in price_match.group(0) and p_val < 50000: p_val *= 56
                            if p_val < 15000: continue
                            
                            # 提取標題：通常排除價格行後的長度最長行
                            lines = [l.strip() for l in full_text.split('\n') if l.strip()]
                            item_title = next((l for l in lines if not re.search(r'(?:₱|PHP|\$|·)', l) and len(l) > 2), "Vehicle")
                            
                            # 取得 ID 並構建完整連結
                            item_id = ""
                            id_match = re.search(r'/item/(\d+)', href)
                            if id_match:
                                item_id = id_match.group(1)
                                full_link = f"https://www.facebook.com/marketplace/item/{item_id}/"
                            else:
                                full_link = "https://www.facebook.com" + href if href.startswith('/') else href

                            processed_raw.append({
                                'title': item_title, 'price': p_val, 'price_display': f"₱{p_val:,}",
                                'link': full_link, 'source': 'FB Marketplace', 'raw_text': full_text.lower()
                            })
                    except: continue

                self._log(f"成功收集 {len(processed_raw)} 筆原始商品資訊")
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
