import requests
from bs4 import BeautifulSoup
import re
from fake_useragent import UserAgent

def check_autodeal_2023():
    ua = UserAgent()
    # AutoDeal uses a different format for some specific model pages
    url = "https://www.autodeal.com.ph/used-cars/search/toyota+vios"
    headers = {"User-Agent": ua.random}
    
    print(f"Inspecting AutoDeal: {url}")
    r = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {r.status_code}")
    
    soup = BeautifulSoup(r.text, 'html.parser')
    # Look for any text '2023'
    matches = soup.find_all(string=re.compile(r'2023'))
    print(f"Found '2023' {len(matches)} times")
    for m in matches[:5]:
        print(f"Context: {m.parent.text[:100]}")

if __name__ == "__main__":
    check_autodeal_2023()
