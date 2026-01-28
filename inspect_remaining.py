import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import urllib.parse
import time

def debug_inspect_sites():
    ua = UserAgent()
    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    # 1. Inspect AutoDeal
    autodeal_url = "https://www.autodeal.com.ph/used-cars/search/toyota+vios"
    print(f"Inspecting AutoDeal: {autodeal_url}")
    try:
        r = requests.get(autodeal_url, headers=headers, timeout=15)
        print(f"AutoDeal Status: {r.status_code}")
        with open("autodeal_debug.html", "w", encoding="utf-8") as f:
            f.write(r.text)
        
        soup = BeautifulSoup(r.text, 'html.parser')
        # Check for listings
        items = soup.find_all(class_=lambda x: x and ('search-result' in x or 'card' in x or 'listing' in x))
        print(f"AutoDeal potential items found: {len(items)}")
    except Exception as e:
        print(f"AutoDeal Error: {e}")

    # 2. Inspect Automart
    automart_url = "https://automart.ph/used-cars?q=toyota%20vios"
    print(f"\nInspecting Automart: {automart_url}")
    try:
        r = requests.get(automart_url, headers=headers, timeout=15)
        print(f"Automart Status: {r.status_code}")
        with open("automart_debug.html", "w", encoding="utf-8") as f:
            f.write(r.text)
        
        soup = BeautifulSoup(r.text, 'html.parser')
        # Check for listings
        items = soup.find_all(class_=lambda x: x and ('Card' in x or 'vehicle' in x or 'item' in x))
        print(f"Automart potential items found: {len(items)}")
    except Exception as e:
        print(f"Automart Error: {e}")

if __name__ == "__main__":
    debug_inspect_sites()
