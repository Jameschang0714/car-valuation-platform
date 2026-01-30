from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import time
import random

class PhilkotseScraper:
    def __init__(self):
        self.base_url = "https://philkotse.com"

    def search(self, make, model, year, fuzzy_search=True):
        search_items = []
        
        # Format strings for URLs
        make_slug = make.lower().replace(" ", "-")
        model_slug = model.lower().replace(" ", "-") if model else ""
        
        # Handle empty year safely
        target_year = None
        if year and str(year).isdigit():
             target_year = int(year)
        
        # Define paths to search
        paths = []
        if model_slug and target_year:
            paths = [
                f"/{make_slug}-{model_slug}-year-{target_year}-for-sale",
                f"/infinite-scroll/used-{make_slug}-{model_slug}-for-sale?pageIndex=1",
                f"/cars-for-sale?q={urllib.parse.quote(f'{make} {model} {target_year}')}"
            ]
        elif model_slug:
             paths = [
                f"/{make_slug}-{model_slug}-for-sale",
                f"/cars-for-sale?q={urllib.parse.quote(f'{make} {model}')}"
            ]
        
        # If fuzzy search is enabled and we need more results, we add adjacent years
        search_years = []
        if target_year:
            search_years = [target_year]
            if fuzzy_search:
                search_years.extend([target_year - 1, target_year + 1])
                # Only add specific year paths if model is present
                if model_slug:
                     for fy in [target_year - 1, target_year + 1]:
                        paths.append(f"/{make_slug}-{model_slug}-year-{fy}-for-sale")

        # Deduplicate paths while preserving order
        unique_paths = []
        
        # KEY FIX: If model is empty or contains spaces (likely a keyword like "Wing Van"),
        # switch to generic search query instead of strict URL path
        use_generic_search = False
        if not model or " " in model:
             use_generic_search = True
        
        if use_generic_search:
             # Case 1: Brand Only Search (Model is empty)
             if not model:
                  # Try specific brand paths first, they are more reliable than ?q=
                  unique_paths.append(f"/used-{make_slug}-for-sale")
                  unique_paths.append(f"/{make_slug}-for-sale")

             # Construct generic query: Make + Model (which might be "Wing Van")
             query_parts = [make]
             if model: query_parts.append(model)
             # If exact year provided, add it
             if year and str(year).isdigit(): query_parts.append(str(year))
             
             q_str = urllib.parse.quote(" ".join(query_parts))
             unique_paths.append(f"/cars-for-sale?q={q_str}")
             # Backup: Try simpler query if complex one fails (e.g. just "Shacman")
             if len(query_parts) > 1:
                 unique_paths.append(f"/cars-for-sale?q={urllib.parse.quote(make)}")
        else:
             # Original logic for strict Make-Model path
             for p in paths:
                if p not in unique_paths: unique_paths.append(p)
             # Fallback for strict mode too: Add general search
             unique_paths.append(f"/cars-for-sale?q={urllib.parse.quote(make)}")

        seen_links = set()
        
        for path in unique_paths:
            if len(search_items) >= 20: break # Stop if we have enough
            
            url = self.base_url + path if not path.startswith("http") else path
            
            try:
                # Log request
                with open("scraper_debug.log", "a", encoding="utf-8") as f:
                     f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Philkotse: 嘗試抓取 {url}\n")

                # Use curl_cffi for cloud-safe requests
                response = cffi_requests.get(
                    url, 
                    impersonate="chrome120", 
                    timeout=30
                )
                
                if response.status_code == 404:
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                # Reverting to broad selectors but relying on seen_links for dedup
                listings = soup.select('.col-4, .list-car-item, .item, .car-item')
                
                for item in listings:
                    try:
                        title_elem = item.select_one('h3.title, .item-title, .title, a[title]')
                        price_elem = item.select_one('.price, .item-price, .amount')
                        link_elem = item.select_one('a[href*="/"]')

                        if title_elem and price_elem:
                            title = title_elem.get_text(strip=True)
                            price_text = price_elem.get_text(strip=True)
                            link = link_elem['href'] if link_elem else ""
                            
                            if not link.startswith('http'):
                                link = self.base_url + link
                            
                            # DEDUPLICATION CHECK
                            if link in seen_links: continue
                            
                            # Image extraction
                            image_url = ""
                            img_elem = item.select_one('img')
                            if img_elem:
                                image_url = img_elem.get('data-src') or img_elem.get('src') or ""
                            
                            # Date extraction
                            date_str = "N/A"
                            if image_url:
                                match = re.search(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', image_url)
                                if match:
                                    date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

                            # --- FILTERING LOGIC ---
                            # (Same logic as before, ensuring relevance)
                            is_relevant = False
                            
                            # 1. Exact make match in title
                            title_lower = title.lower()
                            if make.lower() in title_lower:
                                 is_relevant = True
                            
                            # 2. Query words match
                            if not is_relevant and use_generic_search:
                                 # strict check on valid keywords
                                 q_keywords = [k.lower() for k in query_parts if len(k) > 2] 
                                 if q_keywords and all(k in title_lower for k in q_keywords):
                                      is_relevant = True

                            if is_relevant:
                                 if model:
                                      # Relaxed model check
                                      pass 

                            if is_relevant:
                                # Match ANY of the target years IF target_year is set
                                matched_year = True
                                if search_years:
                                     matched_year = any(str(y) in title for y in search_years)
                                
                                if matched_year:
                                    price = self._parse_price(price_text)
                                    if price > 0:
                                        seen_links.add(link)
                                        search_items.append({
                                            'title': title,
                                            'price': price,
                                            'price_display': price_text.strip(),
                                            'link': link,
                                            'source': 'Philkotse',
                                            'image': image_url,
                                            'date': date_str
                                        })
                    except Exception as e:
                        print(f"Error parsing item: {e}")
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                
            # Removed the single-path break; let it iterate to find more results
            # if search_items: break 
            
            time.sleep(random.uniform(1, 2))
            
        return search_items

    def _parse_price(self, price_str):
        digits = re.sub(r'[^\d]', '', str(price_str))
        return int(digits) if digits else 0

    def _extract_date(self, item):
        try:
            # Extract date from image URL (e.g., .../2026/01/27/...)
            img = item.select_one('img')
            if img:
                src = img.get('data-src') or img.get('src')
                if src:
                    match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', src)
                    if match:
                        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        except: pass
        return "N/A"

if __name__ == "__main__":
    s = PhilkotseScraper()
    res = s.search("Toyota", "Vios", "2023", fuzzy_search=True)
    print(f"Results: {len(res)}")
    for r in res[:3]: print(r)
