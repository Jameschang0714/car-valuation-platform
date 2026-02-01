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
        self._log(f"開始搜尋 {make} {model} {year} (行動版模式)")
        try:
            with sync_playwright() as p:
                self._log("正在啟動 Chromium (模擬 iPhone)...")
                # 使用 Playwright 內建的 iPhone 13 模擬參數
                iphone = p.devices['iPhone 13']
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as b_err:
                    self._log(f"瀏覽器啟動失敗: {b_err}")
                    raise b_err

                self._log("建立行動版瀏覽器內容...")
                context = browser.new_context(
                    **iphone,
                    locale="en-PH"
                )
                page = context.new_page()
                
                query = f"{make} {model}"
                if year: query += f" {year}"
                
                # 改用行動版網址 m.facebook.com
                url = f"https://m.facebook.com/marketplace/search/?query={query.replace(' ', '%20')}"
                
                self._log(f"正在前往行動版 Marketplace: {url}")
                page.goto(url, wait_until="networkidle", timeout=60000)
                
                self._log("執行行動版頁面診斷...")
                time.sleep(random.uniform(5, 8))
                
                title = page.title()
                content_len = len(page.content())
                self._log(f"標題: {title}, 內容長度: {content_len}")

                # 行動版通常也會彈出登入提示，嘗試關閉
                page.keyboard.press("Escape")
                
                # 滾動以觸發加載 (行動版滾動方式與桌面版略有不同)
                for _ in range(2):
                    page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(2)

                self._log("提取行動版商品連結...")
                # 行動版連結特徵
                all_links = page.query_selector_all('a[href*="/marketplace/item/"]')
                
                self._log(f"發現 {len(all_links)} 個潛在連結，開始行動版解析...")
                processed_raw = []
                
                for link in all_links:
                    try:
                        href = link.get_attribute('href') or ""
                        if "/marketplace/item/" in href:
                            # 行動版文字結構通常與桌面版不同，抓取整個區塊文字
                            text = link.evaluate("el => el.innerText")
                            
                            if not text or len(text) < 5: continue
                            
                            price_match = re.search(r'(?:₱|PHP|\$)\s*([\d,.]+)', text)
                            if price_match:
                                p_str = price_match.group(1).replace(",", "")
                                try:
                                    if '.' in p_str and p_str.count('.') == 1: p_val = int(float(p_str))
                                    else: p_val = int(p_str.replace('.', ''))
                                except: continue
                                
                                if '$' in price_match.group(0) and p_val < 50000: p_val *= 56
                                if p_val < 15000: continue
                                
                                # 行動版標題提取優化
                                lines = [l.strip() for l in text.split('\n') if l.strip()]
                                # 過濾掉價格與地點，剩下的第一行通常是標題
                                filtered_lines = [l for l in lines if not re.search(r'(?:₱|PHP|\$|·)', l)]
                                item_title = filtered_lines[0] if filtered_lines else "Vehicle"
                                
                                full_link = href
                                if href.startswith('/'): full_link = "https://www.facebook.com" + href
                                elif "facebook.com" not in href: full_link = "https://www.facebook.com/marketplace/item/" + href.split('/')[-1]

                                processed_raw.append({
                                    'title': item_title, 'price': p_val, 'price_display': f"₱{p_val:,}",
                                    'link': full_link, 'source': 'FB Marketplace', 'raw_text': text.lower()
                                })
                    except: continue

                self._log(f"初步獲取 {len(processed_raw)} 筆符合特徵的原始資料，開始品牌/年份過濾...")
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
