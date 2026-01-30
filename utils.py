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

TRANSLATIONS = {
    'en': {
        'app_title': '🇵🇭 Philippines Used Car Price Searcher',
        'app_subtitle': 'Mabuhay! Input car details to search across major Philippine platforms. (v3.3.2 - Stable)',
        'search_params': 'Search Parameters',
        'make': 'Make (Brand)',
        'model': 'Model',
        'year': 'Year',
        'platforms': 'Platforms',
        'search_btn': 'Start Search / Tara na!',
        'searching': 'Searching {} {} {} ... Sandali lang po (Wait a moment)...',
        'crawling': 'Crawling {}...',
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
        'language': 'Language / 語言'
    },
    'zh': {
        'app_title': '🇵🇭 菲律賓二手車行情搜尋器',
        'app_subtitle': '輸入車輛資訊，自動搜尋菲律賓各大拍賣平台行情。(版本: 3.3.2 - 雲端偵錯版)',
        'search_params': '搜尋條件',
        'make': '品牌 (Make)',
        'model': '車型 (Model)',
        'year': '年份 (Year)',
        'platforms': '平台選擇',
        'search_btn': '開始搜尋',
        'searching': '正在搜尋 {} {} {} ...',
        'crawling': '正在爬取 {}...',
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
        'language': 'Language / 語言'
    }
}

