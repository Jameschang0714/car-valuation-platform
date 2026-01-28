from curl_cffi import requests as cffi_requests
import requests
import urllib.parse
from bs4 import BeautifulSoup

def test_bypass():
    url = "https://www.carousell.ph/search/Toyota%20Vios%202023/?category_id=32&sort_by=3"
    print(f"Targeting: {url}")
    
    # 1. Standard Requests (Expected Fail)
    print("\n--- Testing Standard Requests ---")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
    except Exception as e:
        print(f"Standard Error: {e}")

    # 2. Curl CFFI (Expected Success)
    print("\n--- Testing Curl CFFI (Impersonating Chrome 120) ---")
    try:
        # impersontate='chrome120' mimics the exact TLS handshake of Chrome
        r = cffi_requests.get(url, impersonate="chrome120", timeout=15)
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            title = soup.title.string.strip() if soup.title else "No Title"
            print(f"Page Title: {title}")
            
            # Check for listings presence
            cards = soup.select('div[data-testid^="listing-card"]')
            print(f"Listings found: {len(cards)}")
            
            with open("carousell_bypass.html", "w", encoding="utf-8") as f:
                f.write(r.text)
    except Exception as e:
        print(f"CFFI Error: {e}")

if __name__ == "__main__":
    test_bypass()
