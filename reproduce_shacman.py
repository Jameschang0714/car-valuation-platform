
import importlib
import time
from philkotse_scraper import PhilkotseScraper
from autodeal_scraper import AutoDealScraper
from automart_scraper import AutomartScraper
from carousell_scraper import CarousellScraper

def test_search(make, model, year, description):
    print(f"\n--- Testing: {description} ({make} {model} {year}) ---")
    
    scrapers = [
        PhilkotseScraper(),
        AutoDealScraper(),
        # AutomartScraper(), # Automart API calls might result in 403 locally sometimes, keeping it for now
        CarousellScraper()
    ]
    
    for scraper in scrapers:
        name = scraper.__class__.__name__
        try:
            start = time.time()
            # Passing empty strings/None if not provided
            results = scraper.search(make, model or "", year or "")
            duration = time.time() - start
            print(f"[{name}] Found {len(results)} items in {duration:.2f}s")
            if len(results) > 0:
                print(f"   Example: {results[0]['title']} - {results[0]['link']}")
        except Exception as e:
            print(f"[{name}] CRASHED: {e}")

if __name__ == "__main__":
    # 1. Test Shacman (Brand Only)
    test_search("Shacman", "", "", "Brand Only: Shacman")
    
    # 2. Test Wing Van (Keyword as Model)
    test_search("Shacman", "Wing Van", "", "Keyword: Shacman Wing Van")
    
    # 3. Test Dump Truck (Keyword as Model)
    test_search("Isuzu", "Dump Truck", "", "Keyword: Isuzu Dump Truck")
    
    # 4. Test Tractor Head (Keyword as Model)
    test_search("Sinotruk", "Tractor Head", "", "Keyword: Sinotruk Tractor Head")
