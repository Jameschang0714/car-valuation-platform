import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass
import time
import json
from autodeal_scraper import AutoDealScraper
from automart_scraper import AutomartScraper

# Helper to print safely on Windows Console
def safe_print(obj):
    try:
        print(str(obj))
    except UnicodeEncodeError:
        # If simple print fails, try to print representation or escape utf-8
        print(str(obj).encode('utf-8', errors='replace').decode('utf-8', errors='replace')) # This might still fail on cp950 console if not redirected
        # Fallback: print repr
        print(repr(obj))

def test_autodeal():
    print("--- Testing AutoDeal Scraper ---")
    scraper = AutoDealScraper()
    try:
        # Hack to capture response in the scraper? 
        # Easier to just subclass or modify scraper temporarily?
        # Or just use the scraper as is but I need the HTML.
        # I'll just rely on the existing scraper logging?
        # The scraper writes to scraper_debug.log but doesn't dump HTML.
        
        # I will inject a "save html" logic if possible, or just re-request here accurately.
        # But the scraper class handles headers/params.
        # Let's trust the scraper returns 0 results for now, and try to replicate the request *outside* to see HTML.
        # Or I can just patch the scraper method in this script.
        
        results = scraper.search("Toyota", "Vios", "2022")
        print(f"AutoDeal Results Found: {len(results)}")
        safe_print(results)
            
    except Exception as e:
        print(f"AutoDeal Exception: {e}")

def test_automart():
    print("\n--- Testing Automart Scraper ---")
    scraper = AutomartScraper()
    try:
        results = scraper.search("Toyota", "Vios", "2022")
        print(f"Automart Results Found: {len(results)}")
        if results:
            safe_print(results[0])
            # Check fields
            if results[0]['price'] and results[0]['title']:
                print("Automart seems functional.")
            else:
                print("Automart result missing content.")
        else:
            print("Automart returned no results.")
    except Exception as e:
        print(f"Automart Exception: {e}")
        import traceback
        traceback.print_exc()

def debug_autodeal_html():
    print("\n--- Debugging AutoDeal HTML ---")
    from curl_cffi import requests as cffi_requests
    import urllib.parse
    
    # Replicate logic from AutoDealScraper
    base_url = "https://www.autodeal.com.ph"
    make = "Toyota"
    model = "Vios"
    make_slug = make.strip().replace(" ", "-").lower()
    model_slug = model.strip().replace(" ", "-").lower()
    
    # Try the URL that usually works or is tried first
    url = f"{base_url}/used-cars/search/used-car-status/{make_slug}-make/{model_slug}-model/page-1?sort-by=relevance"
    print(f"Fetching: {url}")
    
    try:
        response = cffi_requests.get(
            url, 
            impersonate="chrome120", 
            timeout=30
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            with open("autodeal_debug_live.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("Saved HTML to autodeal_debug_live.html")
        else:
            print("Failed to fetch.")
    except Exception as e:
        print(f"Fetch Error: {e}")

if __name__ == "__main__":
    test_automart()
    test_autodeal()
    debug_autodeal_html()
