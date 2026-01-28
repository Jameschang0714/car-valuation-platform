from autodeal_scraper import AutoDealScraper
import logging
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)

def diagnose():
    # Always save the diagnostic HTML for the first URL attempt
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
    with open("autodeal_diagnostic.html", "w", encoding="utf-8") as f:
        f.write(resp.text)
    
    ad = AutoDealScraper()
    results = ad.search("Toyota", "vios", 2023, fuzzy_search=True)
    print(f"\nResults found: {len(results)}")
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    listings = soup.select('article.card')
    print(f"Number of 'article.card' elements found by manual BS4: {len(listings)}")

if __name__ == "__main__":
    diagnose()
