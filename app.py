import streamlit as st
import pandas as pd
import importlib
import philkotse_scraper
import autodeal_scraper
import carousell_scraper
import automart_scraper
import facebook_scraper

# Force reload modules
importlib.reload(philkotse_scraper)
importlib.reload(autodeal_scraper)
importlib.reload(carousell_scraper)
importlib.reload(automart_scraper)
importlib.reload(facebook_scraper)

from philkotse_scraper import PhilkotseScraper
from autodeal_scraper import AutoDealScraper
from carousell_scraper import CarousellScraper
from automart_scraper import AutomartScraper
from facebook_scraper import FacebookScraper
from utils import calculate_market_price, format_currency, TRANSLATIONS
import time
import re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize Session State
if 'language' not in st.session_state:
    st.session_state.language = 'en'

def t(key):
    return TRANSLATIONS[st.session_state.language].get(key, key)

# Page config
st.set_page_config(page_title=t('app_title'), page_icon="🚗", layout="wide")

# Styling
st.markdown("""
<style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #ff4b4b;
        color: white;
    }
    .price-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 20px;
    }
    .suggested-price {
        font-size: 2.5em;
        font-weight: bold;
        color: #ff4b4b;
    }
</style>
""", unsafe_allow_html=True)

st.title('🇵🇭 Philippines Used Car Price Searcher (v3.4.7 - mbasic FB Mode)')
st.write(t('app_subtitle'))

# Sidebar for inputs
with st.sidebar:
    # Language Switcher
    lang_options = {'English': 'en', '繁體中文': 'zh'}
    selected_lang = st.radio(t('language'), options=list(lang_options.keys()), index=0 if st.session_state.language == 'en' else 1)
    st.session_state.language = lang_options[selected_lang]

    st.divider()
    
    st.header(t('search_params'))
    make = st.text_input(t('make'), value="Toyota")
    # Allow empty model/year for broader search
    model = st.text_input(t('model'), value="", placeholder="Optional (e.g. Vios, Wing Van)")
    year = st.text_input(t('year'), value="", placeholder="Optional (e.g. 2023)")
    
    # Lock Year Toggle (Checkbox logic: lock_year=True means fuzzy_search=False)
    lock_year = st.checkbox(t('lock_year'), value=False, help=t('lock_year_help'))
    fuzzy_search = not lock_year
    
    st.divider()
    
    st.subheader(t('platforms'))
    use_philkotse = st.checkbox("Philkotse", value=True)
    use_autodeal = st.checkbox("AutoDeal", value=True)
    use_automart = st.checkbox("Automart", value=True)
    use_carousell = st.checkbox("Carousell", value=True)
    use_facebook = st.checkbox("FB Marketplace", value=True)

    search_btn = st.button(t('search_btn'), type="primary")

def run_scraper(scraper_class, make, model, year, fuzzy_search):
    scraper = scraper_class()
    source_name = scraper.__class__.__name__.replace("Scraper", "")
    try:
        results = scraper.search(make, model, year, fuzzy_search=fuzzy_search)
        # st.toast(f"{source_name}: 找到 {len(results)} 筆結果") # Streamlit functions cannot be called directly in threads
        return results
    except Exception as e:
        print(f"{source_name} Error: {e}") # Log to console for now
        return []

def parse_date(date_str):
    try:
        if not date_str or date_str == 'N/A': return None
        # Handle simple YYYY-MM-DD
        if re.match(r'\d{4}-\d{2}-\d{2}', str(date_str)):
            return datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        
        # Handle Carousell timestamps (milliseconds)
        if str(date_str).isdigit():
             # Assume ms if large, sec if small
             ts = int(date_str)
             if ts > 1000000000000: ts /= 1000.0
             return datetime.fromtimestamp(ts)
             
    except: pass
    return None

if search_btn:
    st.divider()
    results_container = st.container()
    
    with st.spinner(t('searching').format(make, model, year)):
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Initialize scrapers
        scrapers = []
        if use_philkotse: scrapers.append(PhilkotseScraper())
        if use_autodeal: scrapers.append(AutoDealScraper())
        if use_carousell: scrapers.append(CarousellScraper())
        if use_automart: scrapers.append(AutomartScraper())
        if use_facebook: scrapers.append(FacebookScraper())
        
        all_results = []
        
        # Run searches sequentially
        for i, scraper in enumerate(scrapers):
            source_name = scraper.__class__.__name__.replace("Scraper", "")
            progress_bar.progress((i) / len(scrapers))
            status_text.text(t('crawling').format(source_name))
            
            try:
                results = scraper.search(make, model, year, fuzzy_search=fuzzy_search)
                all_results.extend(results)
                
                # Show status in debug log/toast
                # st.toast(f"{source_name}: {len(results)} results")
            except Exception as e:
                print(f"{source_name} Error: {e}")
                # Log error to file
                with open("scraper_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {source_name} CRASH: {e}\n")
            
            time.sleep(0.5)
        
        progress_bar.progress(100)
        status_text.empty()

    if all_results:
        # Sort by price
        all_results.sort(key=lambda x: x['price'])
        
        # Convert to DataFrame
        df = pd.DataFrame(all_results)
        
        # --- Helper for Display ---
        # 1. Format Price
        # 1. Format Price
        if 'price_display' in df.columns:
            df['Price (PHP)'] = df['price_display']
        else:
            df['Price (PHP)'] = df['price'].apply(lambda x: f"₱{x:,.0f}")
        
        # 2. Format Date & Highlight Logic
        current_time = datetime.now()
        three_months_ago = current_time - timedelta(days=90)
        
        def format_date_display(row):
            d = parse_date(row.get('date'))
            if d:
                date_str = d.strftime("%Y-%m-%d")
                if d >= three_months_ago:
                    return f"🔥 {date_str}" # Highlight recent
                return date_str
            return str(row.get('date', 'N/A'))

        df['Date'] = df.apply(format_date_display, axis=1)
        
        # 3. Create Link Column
        df['Link'] = df['link'] 
        
        # Rename columns for display based on language
        display_df = df.copy()
        # display_df = display_df.rename(columns={'source': 'Source', 'title': 'Title'}) # Optional

        # Display Summary
        st.success(t('success_msg').format(len(all_results)))

        # Display Dataframe with Link Column Config
        st.dataframe(
            display_df[['source', 'title', 'Price (PHP)', 'Date', 'Link']],
            column_config={
                "Link": st.column_config.LinkColumn(t('col_link')),
                "Date": st.column_config.TextColumn(t('col_date'), help=t('col_date_help'))
            },
            hide_index=True,
            use_container_width=True
        )
        # Calculate suggested price
        suggested_price = calculate_market_price(all_results)
        
        # Display summary
        st.markdown(f"""
        <div class="price-card">
            <h3>{t('market_price')}</h3>
            <div class="suggested-price">{format_currency(suggested_price)}</div>
            <p>{t('based_on').format(len(all_results))}</p>
        </div>
        """, unsafe_allow_html=True)
            
        # Data visualization if needed
        st.subheader(t('chart_title'))
        st.scatter_chart(df, x="title", y="price", color="source") # Use original 'title' and 'price' for chart
            
    else:
        st.warning(t('no_results'))


        
        # Add a manual refresh for logs
        if st.toggle("Show Raw Search Results (Debug)"):
             st.json(all_results)

# Debug Console (Always Visible)
with st.expander(t('developer_tools')):
    st.write(t('logs_title'))
    for source, count in st.session_state.get('last_run_logs', {}).items():
        st.write(f"- {source}: {count}")
    
    st.markdown("---")
    st.write(t('detailed_logs'))
    try:
        with open("scraper_debug.log", "r", encoding="utf-8") as f:
            log_content = f.readlines()
            # Show last 50 lines
            st.code("".join(log_content[-50:]))
    except:
        st.write(t('no_logs'))

# Footer
st.markdown("---")
st.caption(f"{t('disclaimer_title')} {t('disclaimer')}")
