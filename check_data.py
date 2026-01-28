import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

def verify_content():
    ua = UserAgent()
    url = "https://philkotse.com/cars-for-sale?q=Ford+Ranger+2022"
    headers = {"User-Agent": ua.random}
    
    response = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {response.status_code}")
    
    # Check if 'Ranger' or '2022' appears in the body at all
    has_ranger = "Ranger" in response.text
    has_year = "2022" in response.text
    print(f"Contains 'Ranger': {has_ranger}")
    print(f"Contains '2022': {has_year}")
    
    # Save full HTML to check structure
    with open("full_page.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    
    soup = BeautifulSoup(response.text, 'html.parser')
    # Use generic search for ANY price or title
    titles = soup.find_all(string=re.compile(r'Ranger|Ford', re.I))
    print(f"Found {len(titles)} potential title fragments")
    for t in titles[:10]:
        print(f"Fragment: {t.strip()}")

if __name__ == "__main__":
    import re
    verify_content()
