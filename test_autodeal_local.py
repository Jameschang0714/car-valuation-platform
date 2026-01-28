from bs4 import BeautifulSoup
import re
import os

def test_autodeal_selectors():
    file_path = r'C:\Users\PH06424\.gemini\antigravity\scratch\ph_car_scraper\autodeal_debug.html'
    if not os.path.exists(file_path):
        print("File not found.")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    
    print("--- Testing Selectors ---")
    
    # 1. article.card
    listings = soup.select('article.card')
    print(f"Selection 'article.card' count: {len(listings)}")
    
    # 如果為 0，嘗試更寬鬆的選擇器
    if len(listings) == 0:
        listings = soup.find_all('article', class_=re.compile(r'card', re.I))
        print(f"Selection 'article[class*=card]' count: {len(listings)}")

    for i, item in enumerate(listings[:5]):
        print(f"\nListing {i+1}:")
        
        # Title
        title_elem = item.find('h4')
        if not title_elem:
            title_elem = item.find(['h3', 'h2', 'a', 'p'], class_=re.compile(r'title|name|info', re.I))
        
        title = title_elem.get_text(strip=True) if title_elem else "N/A"
        print(f"  Title: {title}")
        
        # Price
        price_elem = item.find('span', class_=re.compile(r'listing-price', re.I))
        if not price_elem:
            price_elem = item.find(['span', 'p', 'div'], class_=re.compile(r'price|amount', re.I))
            
        price_text = price_elem.get_text(strip=True) if price_elem else "N/A"
        print(f"  Price: {price_text}")
        
        # Link
        link_elem = item.find('a', class_=re.compile(r'title_click', re.I))
        if not link_elem:
            # 看看 item 的 parent 是否是 link
            parent = item.parent
            if parent.name == 'a' and parent.has_attr('href'):
                link_elem = parent
            else:
                link_elem = item.find('a', href=True)
                
        link = link_elem['href'] if link_elem else "N/A"
        print(f"  Link: {link}")

if __name__ == "__main__":
    test_autodeal_selectors()
