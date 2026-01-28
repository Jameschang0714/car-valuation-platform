import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import time

def test_carousell_stealth():
    ua = UserAgent()
    # Mocking a common browser header set
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }

    url = "https://www.carousell.ph/search/toyota%20vios%202023/?category_id=32"
    
    print(f"Requesting: {url}")
    session = requests.Session()
    
    # Pre-flight to home
    try:
        session.get("https://www.carousell.ph/", headers={"User-Agent": headers["User-Agent"]}, timeout=10)
        time.sleep(2)
        response = session.get(url, headers=headers, timeout=15)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Look for JSON
            json_tag = soup.find('script', id='__NEXT_DATA__')
            print(f"JSON Found: {json_tag is not None}")
            if json_tag:
                print(f"JSON Length: {len(json_tag.string)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_carousell_stealth()
