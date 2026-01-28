from automart_scraper import AutomartScraper
from carousell_scraper import CarousellScraper
import json
import time

def debug_dates():
    print("--- Debugging Automart ---")
    as_ = AutomartScraper()
    res_a = as_.search("Toyota", "Vios", "2023")
    if res_a:
        print(f"Automart Result 1 Date: {res_a[0].get('date')}")
        # We need to see the raw item if possible, but the scraper consumes it.
        # I will modify the scraper temporarily or trust the logs if I add print there.
        # For now let's just see what we got.
    else:
        print("No Automart results found.")

    print("\n--- Debugging Carousell ---")
    cs = CarousellScraper()
    res_c = cs.search("Toyota", "Vios", "2023")
    if res_c:
        print(f"Carousell Result 1 Date: {res_c[0].get('date')}")
    else:
        print("No Carousell results found.")

if __name__ == "__main__":
    debug_dates()
