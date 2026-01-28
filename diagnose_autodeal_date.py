import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

def diagnose_autodeal_date():
    ua = UserAgent()
    base_url = "https://www.autodeal.com.ph"
    url = f"{base_url}/used-cars/search/toyota-vios"
    headers = {"User-Agent": ua.random}
    
    print(f"Fetching {url}...")
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        listings = soup.select('article.card, .search-result-item')
        print(f"Found {len(listings)} listings.")
        
        # Check for JSON-LD
        json_lds = soup.find_all('script', type='application/ld+json')
        print(f"Found {len(json_lds)} JSON-LD blocks.")
        for i, script in enumerate(json_lds):
            print(f"\n--- JSON-LD {i} ---")
            print(script.string[:500]) # Print first 500 chars to check schema type

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    diagnose_autodeal_date()
