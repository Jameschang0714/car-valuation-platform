import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

def diagnose_deep():
    make = "Toyota"
    model = "vios"
    year = 2023
    make_slug = "toyota"
    model_slug = "vios"
    url = f"https://www.autodeal.com.ph/used-cars/search/used-car-status/{make_slug}-make/{model_slug}-model/page-1?sort-by=relevance"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://www.google.com/"
    }
    
    print(f"Testing URL: {url}")
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')
    listings = soup.select('article.card')
    print(f"Number of 'article.card' elements: {len(listings)}")
    
    for i, item in enumerate(listings):
        if "id=\"sort-bar\"" in str(item): continue # Skip header
        
        print(f"\n--- Item {i} (FULL HTML) ---")
        print(item.prettify())
        break # Only need one

if __name__ == "__main__":
    diagnose_deep()
