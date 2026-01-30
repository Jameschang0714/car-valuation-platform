import asyncio
from playwright.async_api import async_playwright
import re
import time

async def run_fb_test(make, model, year):
    async with async_playwright() as p:
        # Launch browser - use a real browser profile or more headers
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        page = await context.new_page()
        
        # Construct FB Marketplace URL
        query = f"{make} {model} {year}"
        encoded_query = query.replace(" ", "%20")
        url = f"https://www.facebook.com/marketplace/manila/search?query={encoded_query}&category_id=vehicles"
        
        print(f"--- Navigating to: {url} ---")
        
        try:
            # Go to URL
            await page.goto(url, wait_until="networkidle", timeout=60000)
            
            # Wait for any potential item to appear (heuristic)
            print("Detecting content structure...")
            
            # Scroll down to trigger lazy loading
            for i in range(3):
                await page.mouse.wheel(0, 800)
                await asyncio.sleep(2)
            
            # Take a fresh screenshot
            await page.screenshot(path="fb_debug_scrolled.png")
            print("Screenshot saved to fb_debug_scrolled.png")
            
            # 1. Try to find by link role (often used for product cards)
            items = await page.query_selector_all('div[role="main"] a[role="link"]')
            if not items:
                # 2. Try more generic anchors
                items = await page.query_selector_all('a[role="link"]')
            
            print(f"Candidate elements found: {len(items)}")
            
            results = []
            for item in items:
                try:
                    text = await item.inner_text()
                    if not text: continue
                    
                    # Normalize text
                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                    
                    # Look for Price Pattern (₱ or PHP)
                    price_match = re.search(r'(?:₱|PHP)\s*([\d,]+)', text)
                    if price_match:
                        price_str = price_match.group(1).replace(",", "")
                        price = int(price_str)
                        
                        if price > 20000: # Heuristic for a car
                            results.append({
                                'lines': lines,
                                'price': price
                            })
                except: continue
                
            # Deduplicate results (FB often repeats items)
            unique_results = []
            seen_texts = set()
            for r in results:
                summary = " | ".join(r['lines'])
                if summary not in seen_texts:
                    unique_results.append(r)
                    seen_texts.add(summary)
            
            print(f"\n--- Extracted {len(unique_results)} Unique Results ---")
            for i, res in enumerate(unique_results[:15]):
                summary = " | ".join(res['lines'])
                print(f"{i+1}. {summary[:150]}...")
                
        except Exception as e:
            print(f"Error during FB crawl: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run_fb_test("Toyota", "Vios", "2022"))
