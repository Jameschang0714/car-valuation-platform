from autodeal_scraper import AutoDealScraper
from philkotse_scraper import PhilkotseScraper
from automart_scraper import AutomartScraper
from carousell_scraper import CarousellScraper
import time

def simulate():
    make, model, year = "Toyota", "vios", 2023
    scrapers = [PhilkotseScraper(), AutoDealScraper(), AutomartScraper(), CarousellScraper()]
    
    print("--- 模擬 UI 搜尋開始 ---")
    for s in scrapers:
        name = s.__class__.__name__
        try:
            res = s.search(make, model, year)
            print(f"{name}: Found {len(res)} results in {len(res) and 1.5}s")
            for r in res[:5]:
                print(f"  - {r['title']}")
                print(f"    Price: {r['price_display']}")
                print(f"    Date: {r.get('date', 'N/A')}")
                print(f"    Link: {r['link'][:100]}...") # Truncate long links
        except Exception as e:
            print(f"{name} 錯誤: {e}")
    print("--- 模擬結束，請檢查 scraper_debug.log ---")

if __name__ == "__main__":
    simulate()
