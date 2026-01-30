import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass
import time
from carousell_scraper import CarousellScraper

def debug_carousell():
    print("--- Debugging Carousell 'Shacman' Search ---")
    scraper = CarousellScraper()
    
    # Simulate the user's query: Make="Shacman", Model="", Year=""
    make = "Shacman"
    model = ""
    year = ""
    
    print(f"Query: Make='{make}', Model='{model}', Year='{year}'")
    
    try:
        # Patching search to print the URL it generates? 
        # Easier to just run it and see the debug log or modify the scraper slightly to print.
        # But I can't easily modify the running class without editing the file.
        # I'll rely on the return value first.
        
        results = scraper.search(make, model, year)
        print(f"Results Found: {len(results)}")
        
        if len(results) == 0:
            print("No results found. Possible reasons:")
            print("1. URL structure incorrect for empty model/year?")
            print("2. Selectors outdated?")
            print("3. Response blocked (403)?")
            
            # Let's try to verify the URL manually here to replicate exactly what the scraper does
            import urllib.parse
            query = f"{make} {model} {year}".strip()
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.carousell.ph/search/{encoded_query}/?category_id=32&sort_by=3"
            print(f"Generated URL: {url}")
            
            # Let's check scraper_debug.log content if possible, but reading file inside script is also fine.
            try:
                with open("scraper_debug.log", "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    print("\n--- Last 5 lines of scraper_debug.log ---")
                    for line in lines[-5:]:
                        print(line.strip())
            except FileNotFoundError:
                print("scraper_debug.log not found.")

        else:
            print("Results found:")
            for item in results[:3]:
                print(item)

    except Exception as e:
        print(f"Exception during search: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_carousell()
