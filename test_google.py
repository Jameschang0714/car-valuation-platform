import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
from fake_useragent import UserAgent
import time
import random

def test_google_simple():
    # Simple query for Carousell listings
    query = 'site:carousell.ph "Toyota" "Vios" "2023"'
    # Or even simpler
    # query = 'site:carousell.ph Toyota Vios 2023'
    
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Testing Google Simple: {url}")
    r = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {r.status_code}")
    
    with open("google_res.html", "w", encoding="utf-8") as f:
        f.write(r.text)
        
    soup = BeautifulSoup(r.text, 'html.parser')
    g_results = soup.select('.g')
    print(f"G blocks found: {len(g_results)}")
    
    # Check for direct 403 or captcha
    if "detected unusual traffic" in r.text or "not a robot" in r.text:
        print("!!! Google CAPTCHA detected !!!")

if __name__ == "__main__":
    test_google_simple()
