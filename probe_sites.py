import requests
from fake_useragent import UserAgent
import os

ua = UserAgent()

def probe(url, filename):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    print(f"Probing {url} ...")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"  Status: {response.status_code}")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"  Saved to {filename}")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    # Test AutoDeal Model Path
    probe("https://www.autodeal.com.ph/used-cars/toyota/vios", "autodeal_model_vios.html")
    
    # Test Automart different paths
    probe("https://automart.ph/buy", "automart_buy.html")
    probe("https://automart.ph/buy/all", "automart_buy_all.html")
    probe("https://automart.ph/buy/all/toyota/vios", "automart_vios_direct.html")
