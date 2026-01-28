import json

def find_key(obj, target, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            current_path = f"{path}.{k}" if path else k
            if target in k.lower():
                print(f"Found '{k}' at path: {current_path} | Value: {v}")
            find_key(v, target, current_path)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            current_path = f"{path}[{i}]"
            find_key(item, target, current_path)

def search():
    with open("automart_dump.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    print("--- Searching for 'price' ---")
    find_key(data, "price")
    
    print("\n--- Searching for 'cars' list path ---")
    # Helper to find where the list of cars is
    def find_list_with_model(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                current_path = f"{path}.{k}" if path else k
                find_list_with_model(v, current_path)
        elif isinstance(obj, list):
            if len(obj) > 0 and isinstance(obj[0], dict) and "car" in obj[0]:
                print(f"List of CARS found at: {path} (Length: {len(obj)})")
            # Recurse anyway
            for i, item in enumerate(obj):
                find_list_with_model(item, f"{path}[{i}]")

    find_list_with_model(data)

if __name__ == "__main__":
    search()
