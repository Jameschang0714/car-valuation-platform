import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import urllib.parse

def debug_philkotse(make, model, year):
    ua = UserAgent()
    search_q = urllib.parse.quote(f"{make} {model} {year}")
    url = f"https://philkotse.com/cars-for-sale?q={search_q}"
    headers = {"User-Agent": ua.random}
    
    print(f"Fetching: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Status: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Save a snippet of the HTML to see the structure
        with open("philkotse_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text[:20000])
        
        # Look for potential listings broadley
        for tag in ['div', 'section', 'li']:
            found = soup.find_all(tag, class_=True)
            for f in found[:5]:
                print(f"Found tag {tag} with class: {f.get('class')}")
                
        # Look for price patterns like '₱' or 'Pesos'
        prices = soup.find_all(string=re.compile(r'₱|P\s?\d|Price'))
        for p in prices[:5]:
            print(f"Potential price text: {p.parent}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import re
    debug_philkotse("Ford", "Ranger", "2022")
