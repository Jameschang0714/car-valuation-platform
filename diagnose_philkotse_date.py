import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

def diagnose_philkotse_date():
    ua = UserAgent()
    url = "https://philkotse.com/toyota-vios-for-sale"
    headers = {"User-Agent": ua.random}
    
    print(f"Fetching {url}...")
    try:
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        listings = soup.select('.col-4, .list-car-item, .item, .car-item')
        print(f"Found {len(listings)} elements. Filtering for real listings...")
        
        real_listings = []
        for item in listings:
            if item.select_one('.price, .item-price, .amount') and item.select_one('h3.title, .item-title, .title, a[title]'):
                real_listings.append(item)
        
        print(f"Filtered to {len(real_listings)} real listings.")

        for i, item in enumerate(real_listings[:1]):
            print(f"\n--- Item {i} HTML ---")
            print(item.prettify())

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    diagnose_philkotse_date()
