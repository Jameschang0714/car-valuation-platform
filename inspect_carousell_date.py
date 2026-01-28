from bs4 import BeautifulSoup
import json

def inspect_carousell():
    with open("carousell_bypass.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    data_tag = soup.find('script', id='__NEXT_DATA__')
    
    if data_tag:
        data = json.loads(data_tag.string)
        
        # Traverse to find meaningful time fields
        def find_time_fields(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if "time" in k.lower() or "ago" in k.lower() or "create" in k.lower():
                        if isinstance(v, (str, int, float)):
                            print(f"Found '{k}' at {path}.{k}: {v}")
                    
                    if isinstance(v, (dict, list)):
                         find_time_fields(v, f"{path}.{k}")
            elif isinstance(obj, list):
                if len(obj) > 0:
                    find_time_fields(obj[0], f"{path}[0]")

        print("--- Searching for time fields ---")
        find_time_fields(data)

if __name__ == "__main__":
    inspect_carousell()
