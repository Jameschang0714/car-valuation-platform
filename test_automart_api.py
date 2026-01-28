from curl_cffi import requests as cffi_requests
import json
import urllib.parse

def test_api():
    base_url = "https://api.automart.ph/products"
    
    # Query for "Toyota Vios 2023"
    # Removing 'fields' param to get everything
    params = {
        "q": "Toyota Vios 2023",
        "product_category_id": 1,
        "limit": 5
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    print(f"Testing API: {url}")
    
    try:
        # Impersonate Chrome 120
        r = cffi_requests.get(url, impersonate="chrome120", timeout=20)
        print(f"Status: {r.status_code}")
        
        if r.status_code == 200:
            data = r.json()
            print("Response JSON keys:", data.keys())
            
            if 'items' in data:
                items = data['items']
                print(f"Found {len(items)} items.")
                if len(items) > 0:
                    print("First item keys:", items[0].keys())
                    print("\nFirst item full:", json.dumps(items[0], indent=2))
                    print("Price check:")
                    # Look for price related keys
                    for k, v in items[0].items():
                        if "price" in k.lower() or "amount" in k.lower() or "srp" in k.lower():
                            print(f"  {k}: {v}")
                    
                    # Also check nested 'car' object if exists
                    if 'car' in items[0]:
                        print("Inside 'car' object:")
                        for k, v in items[0]['car'].items():
                             if "price" in k.lower():
                                print(f"  car.{k}: {v}")
            else:
                # Maybe list is root?
                pass
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
