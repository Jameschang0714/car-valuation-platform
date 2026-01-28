def hunt():
    with open("automart_bypass_toyota-vios.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    # Simple search for currency symbols
    indicators = ["₱", "Php", "PHP"]
    found_any = False
    
    for ind in indicators:
        count = html.count(ind)
        print(f"Count for '{ind}': {count}")
        if count > 0:
            found_any = True
            # Print context for first 5 occurrences
            start = 0
            for i in range(min(5, count)):
                idx = html.find(ind, start)
                if idx != -1:
                    snippet = html[max(0, idx-50):min(len(html), idx+50)].replace("\n", " ")
                    print(f"  Context {i+1}: ...{snippet}...")
                    start = idx + 1

    if not found_any:
        print("No currency symbols found in HTML.")

if __name__ == "__main__":
    hunt()
