import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import re

def inspect_vios_2023():
    ua = UserAgent()
    # Try the most logical URL for Philkotse
    url = "https://philkotse.com/used-toyota-vios-for-sale-in-the-philippines"
    headers = {"User-Agent": ua.random}
    
    print(f"Inspecting: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Status: {response.status_code}")
        
        with open("philkotse_vios.html", "w", encoding="utf-8") as f:
            f.write(response.text)
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Count all divs and their classes
        all_divs = soup.find_all('div')
        print(f"Total divs: {len(all_divs)}")
        
        # Look for the word '2023' in the whole text
        year_matches = soup.find_all(string=re.compile(r'2023'))
        print(f"Found '2023' in text {len(year_matches)} times")
        
        # Print parents of '2023' nodes to find listing structure
        for i, match in enumerate(year_matches[:10]):
            print(f"Match {i}: {match.parent.name} - {match.parent.get('class')} - Text: {match.strip()[:50]}")

        # Search for any price ₱
        prices = soup.find_all(string=re.compile(r'₱'))
        print(f"Found '₱' {len(prices)} times")
        for i, p in enumerate(prices[:5]):
            print(f"Price {i} Parent: {p.parent.name} class={p.parent.get('class')} - {p.strip()}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_vios_2023()
