import os
import json
import pandas as pd


def calculate_market_price(results):
    if not results:
        return 0

    prices = [r['price'] for r in results if r['price'] > 0]
    if not prices:
        return 0

    # Use median to avoid outliers
    df = pd.DataFrame(prices, columns=['price'])
    median_price = df['price'].median()

    # rounding to nearest thousand
    return int(round(median_price, -3))

def format_currency(amount):
    return f"₱{amount:,.0f}"


def calculate_ltv(dealer_price, financing_amount, market_median):
    """
    Calculate Loan-to-Value analysis.
    Returns dict with real_ltv, real_dp, price_gap_pct, or empty dict if invalid.
    """
    if not dealer_price or not financing_amount or not market_median or market_median <= 0:
        return {}

    real_ltv = (financing_amount / market_median) * 100
    real_dp = 100 - real_ltv
    price_gap_pct = ((dealer_price - market_median) / market_median) * 100

    return {
        "real_ltv": round(real_ltv, 2),
        "real_dp": round(real_dp, 2),
        "price_gap_pct": round(price_gap_pct, 2),
        "market_median": market_median,
        "dealer_price": dealer_price,
        "financing_amount": financing_amount,
    }


def ai_filter_listings(car_query, listings):
    """
    Use Gemini to filter out listings that don't match the target vehicle variant.
    Returns (filtered_listings, removed_listings, filter_message).
    Falls back to returning all listings if Gemini is unavailable.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not listings or len(listings) <= 1:
        return listings, [], None

    # Build compact payload for Gemini (title + price only, save tokens)
    items = []
    for i, r in enumerate(listings):
        items.append({"idx": i, "title": r.get('title', ''), "price": r.get('price', 0)})

    prompt = f"""You are an automotive pricing expert. The target vehicle is: "{car_query}"

Below are {len(items)} search results from Philippine used car platforms. Determine which listings match the target vehicle (same or very similar variant).

Rules:
- KEEP: Same brand, same model name, similar year (±1), same or unspecified trim/transmission
- REMOVE: Clearly different trim (XE vs XLE), different transmission (MT vs AT/CVT), different model (Vios vs Altis)
- If title information is insufficient to determine, DEFAULT TO KEEP

Listings:
{json.dumps(items, ensure_ascii=False)}

Respond with ONLY valid JSON (no markdown, no explanation):
{{"keep": [0, 1, 3], "remove": [2, 4], "remove_reasons": {{"2": "MT vs CVT", "4": "XE vs XLE"}}}}"""

    try:
        import urllib.request

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024,
                "responseMimeType": "application/json"
            }
        })

        req = urllib.request.Request(
            url,
            data=payload.encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        # Parse Gemini response
        text = result['candidates'][0]['content']['parts'][0]['text']
        parsed = json.loads(text)

        keep_indices = set(parsed.get('keep', []))
        remove_indices = set(parsed.get('remove', []))
        remove_reasons = parsed.get('remove_reasons', {})

        # If Gemini returned neither keep nor remove, return all
        if not keep_indices and not remove_indices:
            return listings, [], None

        # Build filtered and removed lists
        filtered = []
        removed = []
        for i, r in enumerate(listings):
            if i in remove_indices:
                r['_remove_reason'] = remove_reasons.get(str(i), 'Variant mismatch')
                removed.append(r)
            else:
                filtered.append(r)

        # Safety: if AI removed everything, return original
        if not filtered:
            return listings, [], "AI filter returned empty results, showing all"

        # Build message
        if removed:
            examples = [r.get('title', '')[:40] for r in removed[:3]]
            msg = f"AI filtered {len(removed)} mismatched listings ({', '.join(examples)})"
        else:
            msg = None

        return filtered, removed, msg

    except Exception as e:
        print(f"[AI Filter] Error: {e}")
        return listings, [], f"AI filter unavailable: {e}"


TRANSLATIONS = {
    'en': {
        'app_title': '🇵🇭 Philippines Used Car Price Searcher',
        'app_subtitle': 'Mabuhay! Input car details to search across major Philippine platforms.',
        'search_params': 'Search Parameters',
        'make': 'Make (Brand)',
        'model': 'Model',
        'year': 'Year',
        'platforms': 'Platforms',
        'search_btn': 'Start Search / Tara na!',
        'searching': 'Searching {} {} {} ... Sandali lang po (Wait a moment)...',
        'crawling': 'Crawling {}...',
        'crawling_parallel': 'Crawling all platforms in parallel...',
        'success_msg': 'Ayos! (Great!) Search complete! Found {} results.',
        'no_results': 'Naku, sayang! (Oh no!) No vehicles found matching your criteria. Try different keywords.',
        'developer_tools': '🛠️ Developer Tools',
        'logs_title': 'Scraper Logs:',
        'detailed_logs': 'Detailed Debug Log (scraper_debug.log):',
        'no_logs': 'No detailed logs available.',
        'disclaimer_title': 'Paalala (Note):',
        'disclaimer': 'Data is for reference only. Actual prices depend on the platform and vehicle condition.',
        'col_link': 'Link',
        'col_date': 'Posted Date',
        'col_date_help': '🔥 indicates posted within 3 months (Bago!)',
        'market_price': 'Suggested Market Price',
        'based_on': 'Calculated based on {} results',
        'chart_title': '📈 Price Distribution',
        'language': 'Language / 語言',
        'lock_year': 'Lock Year (Exact search)',
        'lock_year_help': 'When checked, only searches for the exact year. Uncheck to include +/- 1 year.',
        'ltv_title': '📊 LTV Analysis Tool',
        'ltv_dealer_price': 'Dealer Quoted Price (PHP)',
        'ltv_financing': 'Financing Amount (PHP)',
        'ltv_market_median': 'Market Median Price',
        'ltv_price_gap': 'Price Gap vs Market',
        'ltv_real_ltv': 'Real LTV',
        'ltv_real_dp': 'Real Down Payment',
        'ai_filter_label': '🤖 AI Smart Filter',
        'ai_filter_removed': 'AI filtered {} mismatched variant listings',
        'ai_filter_show_removed': 'Show removed listings',
        'ai_filter_no_key': 'Set GEMINI_API_KEY in .env to enable AI variant filtering',
    },
    'zh': {
        'app_title': '🇵🇭 菲律賓二手車行情搜尋器',
        'app_subtitle': '輸入車輛資訊，自動搜尋菲律賓各大拍賣平台行情。',
        'search_params': '搜尋條件',
        'make': '品牌 (Make)',
        'model': '車型 (Model)',
        'year': '年份 (Year)',
        'platforms': '平台選擇',
        'search_btn': '開始搜尋',
        'searching': '正在搜尋 {} {} {} ...',
        'crawling': '正在爬取 {}...',
        'crawling_parallel': '正在並行爬取所有平台...',
        'success_msg': '搜尋完成！共找到 {} 筆結果。',
        'no_results': '找不到符合條件的車輛，請嘗試更換型號關鍵字。',
        'developer_tools': '🛠️ 開發者偵錯面板',
        'logs_title': '各平台抓取日誌：',
        'detailed_logs': '詳細爬蟲執行日誌 (scraper_debug.log)：',
        'no_logs': '目前尚無詳細日誌。',
        'disclaimer_title': '注意：',
        'disclaimer': '本數據僅供參考，實際價格以平台及實車狀況為準。',
        'col_link': '連結',
        'col_date': '刊登日期',
        'col_date_help': '🔥 代表三個月內的新刊登',
        'market_price': '建議市場成交價',
        'based_on': '基於 {} 筆搜尋結果計算而成',
        'chart_title': '📈 價格分佈',
        'language': 'Language / 語言',
        'lock_year': '鎖定年份 (精確搜尋)',
        'lock_year_help': '勾選後僅搜尋輸入的年份。取消勾選則包含前後一年的結果。',
        'ltv_title': '📊 LTV 分析工具',
        'ltv_dealer_price': '中間商報價 (PHP)',
        'ltv_financing': '貸款金額 (PHP)',
        'ltv_market_median': '市場中位價',
        'ltv_price_gap': '市場溢價',
        'ltv_real_ltv': 'Real LTV',
        'ltv_real_dp': '實際頭期款',
        'ai_filter_label': '🤖 AI 智慧過濾',
        'ai_filter_removed': 'AI 已過濾 {} 筆不符合車型的結果',
        'ai_filter_show_removed': '查看被剔除的清單',
        'ai_filter_no_key': '請在 .env 設定 GEMINI_API_KEY 以啟用 AI 車型過濾',
    }
}
