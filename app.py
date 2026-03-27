import os
import streamlit as st
import pandas as pd
import importlib
import time
import re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

import philkotse_scraper
import autodeal_scraper
import carousell_scraper
import automart_scraper
import allcars_scraper
import carempire_scraper
import ugarte_scraper

# Force reload modules
importlib.reload(philkotse_scraper)
importlib.reload(autodeal_scraper)
importlib.reload(carousell_scraper)
importlib.reload(automart_scraper)
importlib.reload(allcars_scraper)
importlib.reload(carempire_scraper)
importlib.reload(ugarte_scraper)

from philkotse_scraper import PhilkotseScraper
from autodeal_scraper import AutoDealScraper
from carousell_scraper import CarousellScraper
from automart_scraper import AutomartScraper
from allcars_scraper import AllCarsScraper
from carempire_scraper import CarEmpireScraper
from ugarte_scraper import UgarteScraper
from utils import calculate_market_price, format_currency, calculate_ltv, ai_filter_listings, TRANSLATIONS

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

st.title('🇵🇭 Philippines Used Car Price Searcher (v4.0 - AI Filter)')
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
    use_allcars = st.checkbox("AllCars.ph", value=True)
    use_carempire = st.checkbox("CarEmpire", value=True)
    use_ugarte = st.checkbox("UgarteCars", value=True)

    search_btn = st.button(t('search_btn'), type="primary")


def _run_one_scraper(scraper, make, model, year, fuzzy_search):
    """Run a single scraper with error handling. Used by ThreadPoolExecutor."""
    source_name = scraper.__class__.__name__.replace("Scraper", "")
    try:
        results = scraper.search(make, model, year, fuzzy_search=fuzzy_search)
        return source_name, results
    except Exception as e:
        print(f"{source_name} Error: {e}")
        with open("scraper_debug.log", "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {source_name} CRASH: {e}\n")
        return source_name, []


def parse_date(date_str):
    try:
        if not date_str or date_str == 'N/A': return None
        if re.match(r'\d{4}-\d{2}-\d{2}', str(date_str)):
            return datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        if str(date_str).isdigit():
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
        status_text.text(t('crawling_parallel'))

        # Initialize scrapers based on user selection
        scrapers = []
        if use_philkotse: scrapers.append(PhilkotseScraper())
        if use_autodeal: scrapers.append(AutoDealScraper())
        if use_carousell: scrapers.append(CarousellScraper())
        if use_automart: scrapers.append(AutomartScraper())
        if use_allcars: scrapers.append(AllCarsScraper())
        if use_carempire: scrapers.append(CarEmpireScraper())
        if use_ugarte: scrapers.append(UgarteScraper())

        all_results = []
        scraper_stats = {}  # Track per-platform counts

        # --- Parallel execution with ThreadPoolExecutor ---
        if scrapers:
            with ThreadPoolExecutor(max_workers=len(scrapers)) as executor:
                futures = {
                    executor.submit(_run_one_scraper, s, make, model, year, fuzzy_search): s
                    for s in scrapers
                }
                completed = 0
                for future in as_completed(futures):
                    source_name, results = future.result()
                    all_results.extend(results)
                    scraper_stats[source_name] = len(results)
                    completed += 1
                    progress_bar.progress(completed / len(scrapers))
                    status_text.text(f"{source_name}: {len(results)} results")

        progress_bar.progress(100)
        status_text.empty()

    # --- Display per-platform summary ---
    if scraper_stats:
        cols = st.columns(len(scraper_stats))
        for i, (name, count) in enumerate(scraper_stats.items()):
            with cols[i]:
                st.metric(name, f"{count} results")

    if all_results:
        # --- AI Smart Filter ---
        car_query = f"{year} {make} {model}".strip()
        removed_listings = []
        filter_msg = None

        if os.getenv("GEMINI_API_KEY") and model:
            with st.spinner(t('ai_filter_label')):
                all_results, removed_listings, filter_msg = ai_filter_listings(car_query, all_results)

        # Show filter results
        if removed_listings:
            st.info(t('ai_filter_removed').format(len(removed_listings)))
            with st.expander(t('ai_filter_show_removed')):
                removed_df = pd.DataFrame(removed_listings)
                if '_remove_reason' in removed_df.columns:
                    st.dataframe(
                        removed_df[['source', 'title', 'price', '_remove_reason']].rename(
                            columns={'_remove_reason': 'Reason'}
                        ),
                        hide_index=True,
                        use_container_width=True
                    )
        elif filter_msg and "unavailable" in str(filter_msg):
            pass  # Silently skip if API error
        elif not os.getenv("GEMINI_API_KEY") and model:
            st.caption(t('ai_filter_no_key'))

        # Sort by price
        all_results.sort(key=lambda x: x['price'])

        # Convert to DataFrame
        df = pd.DataFrame(all_results)

        # --- Helper for Display ---
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
                    return f"🔥 {date_str}"
                return date_str
            return str(row.get('date', 'N/A'))

        df['Date'] = df.apply(format_date_display, axis=1)

        # 3. Create Link Column
        df['Link'] = df['link']

        # Display Summary
        st.success(t('success_msg').format(len(all_results)))

        # Display Dataframe
        st.dataframe(
            df[['source', 'title', 'Price (PHP)', 'Date', 'Link']],
            column_config={
                "Link": st.column_config.LinkColumn(t('col_link')),
                "Date": st.column_config.TextColumn(t('col_date'), help=t('col_date_help'))
            },
            hide_index=True,
            use_container_width=True
        )

        # Calculate suggested price
        suggested_price = calculate_market_price(all_results)

        # Display market price card
        st.markdown(f"""
        <div class="price-card">
            <h3>{t('market_price')}</h3>
            <div class="suggested-price">{format_currency(suggested_price)}</div>
            <p>{t('based_on').format(len(all_results))}</p>
        </div>
        """, unsafe_allow_html=True)

        # --- LTV Analysis Tool ---
        with st.expander(t('ltv_title')):
            col_a, col_b = st.columns(2)
            with col_a:
                dealer_price = st.number_input(
                    t('ltv_dealer_price'),
                    min_value=0,
                    value=0,
                    step=10000,
                    format="%d"
                )
            with col_b:
                financing_amount = st.number_input(
                    t('ltv_financing'),
                    min_value=0,
                    value=0,
                    step=10000,
                    format="%d"
                )

            if dealer_price > 0 and financing_amount > 0 and suggested_price > 0:
                ltv = calculate_ltv(dealer_price, financing_amount, suggested_price)

                if ltv:
                    st.divider()

                    # Market median
                    st.markdown(f"**{t('ltv_market_median')}:** {format_currency(suggested_price)}")

                    # Price gap with color indicator
                    gap = ltv['price_gap_pct']
                    if gap > 10:
                        gap_icon = "🔴"
                    elif gap > 5:
                        gap_icon = "🟡"
                    elif gap > -5:
                        gap_icon = "🟢"
                    else:
                        gap_icon = "🔵"
                    st.markdown(f"**{t('ltv_price_gap')}:** {gap_icon} {gap:+.1f}%")

                    # Real LTV
                    ltv_val = ltv['real_ltv']
                    if ltv_val >= 95:
                        ltv_icon = "🔴"
                    elif ltv_val >= 85:
                        ltv_icon = "🟡"
                    else:
                        ltv_icon = "🟢"
                    st.markdown(f"**{t('ltv_real_ltv')}:** {ltv_icon} {ltv_val:.1f}%")

                    # Real DP
                    st.markdown(f"**{t('ltv_real_dp')}:** {ltv['real_dp']:.1f}%")

        # Data visualization
        st.subheader(t('chart_title'))
        st.scatter_chart(df, x="title", y="price", color="source")

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
            st.code("".join(log_content[-50:]))
    except:
        st.write(t('no_logs'))

# Footer
st.markdown("---")
st.caption(f"{t('disclaimer_title')} {t('disclaimer')}")
