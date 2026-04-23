import os
import json
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def calculate_market_price(results):
    """
    Advanced market price estimation using multi-anchor statistical blending.
    Aggressive positioning — targets approximately the top 20% (P80) of
    cleaned data with sample-size-dependent weighting and dispersion adjustment.
    """
    if not results:
        return 0

    prices = sorted([r['price'] for r in results if r['price'] > 0])
    n = len(prices)
    if n == 0:
        return 0

    max_price = max(prices)

    if n == 1:
        return int(round(prices[0] / 5000) * 5000)
    if n == 2:
        # Weighted toward the higher price (aggressive) but never exceed it
        weighted = prices[0] * 0.3 + prices[1] * 0.7
        rounded = int(round(weighted / 5000) * 5000)
        return min(rounded, max_price)

    arr = np.array(prices, dtype=float)

    # Phase 1: IQR-based outlier removal
    q1 = np.percentile(arr, 25)
    q3 = np.percentile(arr, 75)
    iqr = q3 - q1
    fence_low = q1 - 1.5 * iqr
    fence_high = q3 + 1.5 * iqr
    clean = arr[(arr >= fence_low) & (arr <= fence_high)]
    if len(clean) < 3:
        clean = arr  # fallback if too aggressive

    m = len(clean)

    # Phase 2: Multi-anchor percentile blending (aggressive — upper range)
    p62 = np.percentile(clean, 62)
    p72 = np.percentile(clean, 72)
    p80 = np.percentile(clean, 80)
    p88 = np.percentile(clean, 88)

    # Larger samples → trust P80 core more; smaller → blend wider
    if m >= 15:
        w = np.array([0.12, 0.28, 0.38, 0.22])
    elif m >= 8:
        w = np.array([0.18, 0.30, 0.33, 0.19])
    else:
        w = np.array([0.25, 0.32, 0.28, 0.15])

    anchors = np.array([p62, p72, p80, p88])
    base_price = np.dot(anchors, w)

    # Phase 3: Coefficient of variation adjustment
    mu = np.mean(clean)
    cv = np.std(clean) / mu if mu > 0 else 0

    # Tight cluster → confident → slight upward push
    # Wide spread → moderate → less push
    kappa = 1.0 + min(cv * 0.08, 0.03)

    # Phase 4: Sample confidence scaling
    confidence = 1.0 - (0.5 / math.sqrt(max(m, 2)))
    blend = base_price * kappa * (0.92 + 0.08 * confidence)

    # Phase 5: Trimmed mean ceiling (prevents exceeding reasonable upper bound)
    trim_pct = 0.1
    trim_n = max(1, int(m * trim_pct))
    trimmed = clean[trim_n:-trim_n] if m > 2 * trim_n else clean
    ceiling = np.mean(trimmed) * 1.18

    final = min(blend, ceiling)

    # Global cap: never exceed the highest actual price in the dataset
    final = min(final, max_price)

    # Round to nearest 5000
    return int(round(final / 5000) * 5000)

def format_currency(amount):
    return f"₱{amount:,.0f}"


def compute_date_cutoff():
    """
    Business rule for date freshness:
    - Jan-Jun: keep listings from past 6 months
    - Jul-Dec: keep listings from current year (Jan 1)
    """
    now = datetime.now()
    if now.month <= 6:
        return now - timedelta(days=183)
    else:
        return datetime(now.year, 1, 1)


def filter_by_date(listings, cutoff, parse_date_fn):
    """
    Filter listings by date cutoff.
    - Parseable date >= cutoff: keep
    - Parseable date < cutoff: remove (stale)
    - N/A or unparseable date: keep (benefit of the doubt)
    Returns (kept, removed, stats_dict).
    """
    kept = []
    removed = []
    kept_no_date = 0

    for r in listings:
        d = parse_date_fn(r.get('date'))
        if d is None:
            kept.append(r)
            kept_no_date += 1
        elif d >= cutoff:
            kept.append(r)
        else:
            r['_date_filter_reason'] = f"Posted {d.strftime('%Y-%m-%d')}, cutoff {cutoff.strftime('%Y-%m-%d')}"
            removed.append(r)

    stats = {
        'total': len(listings),
        'kept': len(kept),
        'removed_stale': len(removed),
        'kept_no_date': kept_no_date,
        'cutoff': cutoff.strftime('%Y-%m-%d'),
    }
    return kept, removed, stats


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

Below are {len(items)} search results from Philippine used car platforms. Determine which listings match the target vehicle.

Rules:
- KEEP: Same brand, same model, same trim/variant, similar year (±1)
- REMOVE: Different trim level (GLX ≠ GLS ≠ G ≠ GLE, XE ≠ XLE ≠ XLi), different transmission type (MT vs AT/CVT), different model name (Vios vs Altis)
- Trim levels are STRICT: GLX and GLS are DIFFERENT trims, XE and XLE are DIFFERENT trims. Only keep exact trim match.
- If target specifies a trim but listing title does NOT mention any trim, DEFAULT TO KEEP
- If listing title specifies a DIFFERENT trim from the target, REMOVE it

Listings:
{json.dumps(items, ensure_ascii=False)}

Respond with ONLY valid JSON (no markdown, no explanation):
{{"keep": [0, 1, 3], "remove": [2, 4], "remove_reasons": {{"2": "MT vs CVT", "4": "XE vs XLE"}}}}"""

    try:
        import urllib.request

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent"
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
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode('utf-8'))

        # Parse Gemini response (with null checks)
        candidates = result.get('candidates', [])
        if not candidates:
            return listings, [], "AI filter: no candidates in response"
        text = candidates[0].get('content', {}).get('parts', [{}])[0].get('text', '')
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
        'ltv_market_median': 'Suggested Market Price',
        'ltv_price_gap': 'Price Gap vs Market',
        'ltv_real_ltv': 'Real LTV',
        'ltv_real_dp': 'Real Down Payment',
        'ai_filter_label': '🤖 AI Smart Filter',
        'ai_filter_removed': 'AI filtered {} mismatched variant listings',
        'ai_filter_show_removed': 'Show removed listings',
        'ai_filter_no_key': 'Set GEMINI_API_KEY in .env to enable AI variant filtering',
        'date_filter_removed': 'Date filter: removed {} stale listings (cutoff: {})',
        'date_filter_no_date': '{} listings kept without date info',
        'date_filter_show_removed': 'Show date-filtered listings',
        'variant_filter_removed': 'Variant filter: removed {} listings with mismatched trim/spec',
        'variant_filter_show_removed': 'Show variant-filtered listings',
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
        'ltv_market_median': '建議市場價',
        'ltv_price_gap': '市場溢價',
        'ltv_real_ltv': 'Real LTV',
        'ltv_real_dp': '實際頭期款',
        'ai_filter_label': '🤖 AI 智慧過濾',
        'ai_filter_removed': 'AI 已過濾 {} 筆不符合車型的結果',
        'ai_filter_show_removed': '查看被剔除的清單',
        'ai_filter_no_key': '請在 .env 設定 GEMINI_API_KEY 以啟用 AI 車型過濾',
        'date_filter_removed': '日期過濾：移除 {} 筆過期資訊（截止日：{}）',
        'date_filter_no_date': '{} 筆無日期資訊已保留',
        'date_filter_show_removed': '查看被移除的過期清單',
        'variant_filter_removed': '規格過濾：移除 {} 筆不符合車型規格的結果',
        'variant_filter_show_removed': '查看被規格過濾的清單',
    }
}
