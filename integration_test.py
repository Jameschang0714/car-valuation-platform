from philkotse_scraper import PhilkotseScraper
from autodeal_scraper import AutoDealScraper
from carousell_scraper import CarousellScraper
from automart_scraper import AutomartScraper
import json

def run_integration_test(make, model, year, fuzzy):
    print(f"--- Testing {year} {make} {model} (fuzzy={fuzzy}) ---")
    scrapers = [
        PhilkotseScraper(),
        AutoDealScraper(),
        CarousellScraper(),
        AutomartScraper()
    ]
    
    all_results = []
    for s in scrapers:
        name = s.__class__.__name__
        try:
            res = s.search(make, model, year, fuzzy_search=fuzzy)
            print(f"{name}: Found {len(res)} results")
            all_results.extend(res)
        except Exception as e:
            print(f"{name}: ERROR - {e}")
            
    print(f"\nTotal results: {len(all_results)}")
    if all_results:
        print("First 3 titles:")
        for r in all_results[:3]:
            print(f" - [{r['source']}] {r['title']} : {r['price_display']}")
    else:
        print("!!! NO RESULTS FOUND !!!")

if __name__ == "__main__":
    run_integration_test("Toyota", "Vios", "2023", True)
    print("\n")
    run_integration_test("Ford", "Ranger", "2022", True)
