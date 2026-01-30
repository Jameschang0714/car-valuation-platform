from playwright.sync_api import sync_playwright
import time

def debug_attributes():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
        
        url = "https://www.facebook.com/marketplace/manila/search?query=Shacman"
        print(f"Loading {url}...")
        page.goto(url)
        time.sleep(8)
        
        page.keyboard.press("Escape")
        time.sleep(1)
        
        links = page.query_selector_all('a[href*="/marketplace/item/"]')
        print(f"Found {len(links)} marketplace links.")
        
        for i, link in enumerate(links[:10]):
            aria = link.get_attribute('aria-label')
            inner = link.inner_text()
            print(f"\n--- Item {i} ---")
            print(f"ARIA: {aria}")
            print(f"INNER: {inner.replace('\n', ' | ')}")
            
        browser.close()

if __name__ == "__main__":
    debug_attributes()
