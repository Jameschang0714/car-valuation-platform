from curl_cffi import requests as cffi_requests
import urllib.parse
import time
import random
from datetime import datetime, timedelta

class AutomartScraper:
    def __init__(self):
        self.base_url = "https://automart.ph"
        self.api_url = "https://api.automart.ph/products"

    def _extract_base_model(self, model):
        """Extract base model name, stripping variant/spec tokens."""
        if not model:
            return ""
        import re
        spec_tokens = {'gls', 'glx', 'xle', 'xli', 'xe',
                       'at', 'a/t', 'mt', 'm/t', 'cvt', 'automatic', 'manual',
                       'gas', 'diesel', 'dsl', '4x4', '4x2', 'turbo', 'hybrid',
                       'hb', 'sedan', 'wagon'}
        parts = model.split()
        base_parts = []
        for p in parts:
            if p.lower() in spec_tokens or re.match(r'^\d+\.\d+', p):
                break
            base_parts.append(p)
        return " ".join(base_parts) if base_parts else parts[0]

    def _query_api(self, query_str):
        """Send a single API query, return list of raw items."""
        params = {"q": query_str, "limit": 20}
        query_url = f"{self.api_url}?{urllib.parse.urlencode(params)}"
        with open("scraper_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Automart (API): 查詢 {query_url}\n")
        response = cffi_requests.get(query_url, impersonate="chrome120", timeout=15)
        with open("scraper_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Automart: 狀態碼 {response.status_code}\n")
        if response.status_code == 200:
            return response.json().get('items', [])
        return []

    def search(self, make, model, year, fuzzy_search=True):
        results = []
        try:
            base_model = self._extract_base_model(model) if model else ""

            # Build query candidates: base_model first, then full model as fallback
            queries = []
            queries.append(f"{make} {base_model} {year}".strip())
            if model and model.strip() != base_model:
                queries.append(f"{make} {model} {year}".strip())
                # Also try without year for broader match
                queries.append(f"{make} {model}".strip())

            # Try each query until we get results
            items = []
            seen_slugs = set()
            for q in queries:
                fetched = self._query_api(q)
                for item in fetched:
                    slug = item.get('slug', '')
                    if slug and slug not in seen_slugs:
                        seen_slugs.add(slug)
                        items.append(item)
                if items:
                    break  # Got results, stop trying fallbacks

            for i, item in enumerate(items):
                try:
                    title = item.get('title')
                    price = item.get('price_order')
                    slug = item.get('slug')

                    if title and price and slug:
                        link = f"https://automart.ph/used-cars/{slug}"

                        # Post-filter: base_model must appear in title
                        if base_model.lower() in title.lower():
                            date_str = 'N/A'
                            if 'expired_at' in item and item['expired_at']:
                                try:
                                    exp_date = datetime.strptime(item['expired_at'].split(' ')[0], "%Y-%m-%d")
                                    est_created = exp_date - timedelta(days=60)
                                    date_str = est_created.strftime("%Y-%m-%d")
                                except: pass

                            results.append({
                                'title': title,
                                'price': int(price),
                                'price_display': f"₱{int(price):,}",
                                'link': link,
                                'source': 'Automart',
                                'date': date_str
                            })
                except Exception as e:
                    print(f"Automart item parse error: {e}")
                    continue

        except Exception as e:
            with open("scraper_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Automart Error: {e}\n")
            print(f"Automart API Error: {e}")

        return results

    def _parse_price(self, price_str):
        # Unused in API mode but kept for compatibility if needed
        return 0
