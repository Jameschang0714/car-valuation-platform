from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import time
import random

class PhilkotseScraper:
    def __init__(self):
        self.base_url = "https://philkotse.com"

    def _extract_base_model(self, model):
        """Extract the base model name from a full spec string.
        e.g. 'Xpander GLS 1.5G AT' -> 'Xpander'
             'Vios XLE CVT' -> 'Vios'
             'Wing Van' -> 'Wing Van' (multi-word model kept)
        """
        if not model:
            return ""
        # Known multi-word models that should NOT be split
        multi_word_models = ['wing van', 'land cruiser', 'hiace commuter', 'civic type r',
                             'hr v', 'br v', 'cr v', 'rav4', 'rav 4']
        model_lower = model.lower().strip()
        for mwm in multi_word_models:
            if model_lower.startswith(mwm):
                return model[:len(mwm)]

        # Spec/variant tokens — stop splitting when we hit one
        spec_tokens = {'gls', 'glx', 'xle', 'xli', 'xe', 'g', 'e', 'j', 's', 'v',
                       'at', 'a/t', 'mt', 'm/t', 'cvt', 'automatic', 'manual',
                       'gas', 'diesel', 'dsl', '4x4', '4x2', '2wd', '4wd',
                       'turbo', 'hybrid', '1.0', '1.2', '1.3', '1.5', '1.5g',
                       '1.6', '1.8', '2.0', '2.4', '2.5', '2.7', '2.8', '3.0'}
        parts = model.split()
        base_parts = []
        for p in parts:
            if p.lower() in spec_tokens or re.match(r'^\d+\.\d+', p):
                break
            base_parts.append(p)
        return " ".join(base_parts) if base_parts else parts[0]

    def search(self, make, model, year, fuzzy_search=True):
        search_items = []

        # Format strings for URLs
        make_slug = make.lower().replace(" ", "-")
        # Use base model name for URL (not full spec string)
        base_model = self._extract_base_model(model) if model else ""
        model_slug = base_model.lower().replace(" ", "-") if base_model else ""

        # Handle empty year safely
        target_year = None
        if year and str(year).isdigit():
             target_year = int(year)

        # Define paths to search — correct Philkotse URL patterns with "used-" prefix
        paths = []
        if model_slug and target_year:
            paths = [
                f"/used-{make_slug}-{model_slug}-year-{target_year}-for-sale",
                f"/{make_slug}-{model_slug}-year-{target_year}-for-sale",
                f"/cars-for-sale?q={urllib.parse.quote(f'{make} {base_model} {target_year}')}"
            ]
        elif model_slug:
             paths = [
                f"/used-{make_slug}-{model_slug}-for-sale",
                f"/{make_slug}-{model_slug}-for-sale",
                f"/cars-for-sale?q={urllib.parse.quote(f'{make} {base_model}')}"
            ]

        # If fuzzy search is enabled and we need more results, we add adjacent years
        search_years = []
        if target_year:
            search_years = [target_year]
            if fuzzy_search:
                search_years.extend([target_year - 1, target_year + 1])
                if model_slug:
                     for fy in [target_year - 1, target_year + 1]:
                        paths.append(f"/used-{make_slug}-{model_slug}-year-{fy}-for-sale")

        # Build unique_paths: structured URLs first, then generic fallback
        unique_paths = []

        if not model:
            # Brand-only search
            unique_paths.append(f"/used-{make_slug}-for-sale")
            unique_paths.append(f"/{make_slug}-for-sale")
        elif model_slug:
            # We have a base model slug — always try structured URLs first
            for p in paths:
                if p not in unique_paths:
                    unique_paths.append(p)

        # Generic search fallback (always add as last resort)
        query_parts = [make]
        if model:
            query_parts.append(model)  # Full model string for search query
        if year and str(year).isdigit():
            query_parts.append(str(year))
        q_str = urllib.parse.quote(" ".join(query_parts))
        unique_paths.append(f"/cars-for-sale?q={q_str}")

        # Final fallback: brand-only search
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
                            is_relevant = False
                            title_lower = title.lower()

                            # 1. Brand match (required)
                            if make.lower() in title_lower:
                                 is_relevant = True

                            # 2. Base model match (if model provided)
                            if is_relevant and base_model:
                                 if base_model.lower() not in title_lower:
                                      is_relevant = False

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
