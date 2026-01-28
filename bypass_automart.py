from curl_cffi import requests as cffi_requests
import requests
import urllib.parse
from bs4 import BeautifulSoup

def test_automart_bypass():
    make = "Toyota"
    model = "Vios"
    year = "2023"
    
    # URL Patterns to try
    # 1. Specific slug from metadata
    urls = [
        "https://automart.ph/used-cars/toyota-vios",
        "https://automart.ph/used-cars/toyota-vios?page=1"
    ]
    
    print("--- Testing Automart with curl_cffi ---")
    
    for url in urls:
        print(f"\nTargeting: {url}")
        try:
            # Impersonate Chrome 120
            r = cffi_requests.get(url, impersonate="chrome120", timeout=20)
            print(f"Status: {r.status_code}")
            print(f"Content-Length: {len(r.text)}")
            
            # Save regardless of status code to inspect the "404 page"
            fname = f"automart_bypass_{url.split('/')[-1] or 'root'}.html"
            with open(fname, "w", encoding="utf-8") as f:
                f.write(r.text)
                
            if r.status_code == 200:
                print("SUCCESS: 200 OK")
            else:
                print("Checking failed response content...")
                
        except Exception as e:
            print(f"Error: {e}")
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_automart_bypass()
