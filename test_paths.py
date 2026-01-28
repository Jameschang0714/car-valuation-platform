import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import re

def test_new_paths():
    ua = UserAgent()
    headers = {"User-Agent": ua.random}
    
    # Path 1: Specific Year URL
    url1 = "https://philkotse.com/toyota-vios-year-2023-for-sale"
    print(f"Testing Path 1: {url1}")
    r1 = requests.get(url1, headers=headers, timeout=15)
    print(f"Status: {r1.status_code}")
    
    # Save a snippet
    with open("path1.html", "w", encoding="utf-8") as f: f.write(r1.text)
    
    # Path 2: Infinite Scroll (Guessing params)
    url2 = "https://philkotse.com/infinite-scroll/used-toyota-vios-for-sale?pageIndex=1"
    print(f"Testing Path 2: {url2}")
    r2 = requests.get(url2, headers=headers, timeout=15)
    print(f"Status: {r2.status_code}")
    
    with open("path2.html", "w", encoding="utf-8") as f: f.write(r2.text)

    # Simple check for content
    for i, r in enumerate([r1, r2]):
        soup = BeautifulSoup(r.text, 'html.parser')
        # Check for prices or titles
        prices = soup.find_all(string=re.compile(r'₱'))
        print(f"Path {i+1} Price count: {len(prices)}")
        if prices:
            print(f"Example price: {prices[0].strip()}")

if __name__ == "__main__":
    test_new_paths()
