import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Page Config
st.set_page_config(
    page_title="Sniper Bot",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Bloomberg" aesthetic and cleaner UI
st.markdown("""
<style>
    /* General App Styling */
    .stApp {
        background-color: #0e1117;
        color: #e0e0e0;
        font-family: 'Roboto', sans-serif;
    }
    
    /* Hide Streamlit Default Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: #1e2127;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #2e323b;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        font-weight: bold;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #0e1117;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e2127;
        border-bottom: 2px solid #00ff00;
    }
    
    /* Dataframe */
    .stDataFrame {
        border: 1px solid #2e323b;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Supabase
@st.cache_resource
def init_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        st.error("❌ Supabase credentials not found in .env")
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"❌ Failed to connect to Supabase: {e}")
        return None

supabase = init_supabase()

# --- Data Engine ---

def fetch_signals_from_db():
    """Fetch all signals from Supabase with error handling"""
    if not supabase:
        return pd.DataFrame()
    
    try:
        response = supabase.table('sniper_signals').select('*').order('created_at', desc=True).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df['created_at'] = pd.to_datetime(df['created_at'])
        return df
    except Exception as e:
        st.error(f"❌ Error fetching signals from database: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300) # Cache for 5 minutes
def fetch_live_prices(tickers):
    """Fetch live prices for a list of tickers using batch download"""
    if not tickers:
        return {}
    
    try:
        # Download batch data
        # Use threads=True for speed
        data = yf.download(tickers, period="1d", interval="1m", group_by='ticker', progress=False, threads=True)
        
        prices = {}
        for ticker in tickers:
            try:
                # Handle MultiIndex or Single Index
                if len(tickers) > 1:
                    df = data[ticker]
                else:
                    df = data
                
                if not df.empty:
                    # Get last valid close
                    # Use 'dropna' to avoid NaNs at the end of the series
                    last_price = df['Close'].dropna().iloc[-1]
                    prices[ticker] = float(last_price)
                else:
                    prices[ticker] = None
            except Exception:
                prices[ticker] = None
        return prices
    except Exception as e:
        st.warning(f"⚠️ Live price fetch failed (using entry prices): {e}")
        return {}

# --- Sidebar ---
st.sidebar.title("🎯 Sniper Control")

# Filters
min_score = st.sidebar.slider("Min Confidence Score", 0, 100, 75)
status_filter = st.sidebar.selectbox("Status", ["All", "OPEN", "CLOSED"], index=1)

if st.sidebar.button("🔄 Force Refresh Data"):
    st.cache_data.clear()
    st.rerun()

# --- Main Data Processing ---
with st.spinner("Fetching market data..."):
    df = fetch_signals_from_db()

    if not df.empty:
        # Apply Filters
        if status_filter != "All":
            df = df[df['status'] == status_filter]
        df = df[df['confidence_score'] >= min_score]
        
        if not df.empty:
            # Fetch Live Prices
            unique_tickers = df['ticker'].unique().tolist()
            live_prices = fetch_live_prices(unique_tickers)
            
            # Calculate Metrics
            # Map live prices, fallback to entry_price if live price is missing/None
            df['current_price'] = df['ticker'].map(live_prices)
            df['current_price'] = df['current_price'].fillna(df['entry_price'])
            
            # Calculate P/L
            df['pl_pct'] = ((df['current_price'] - df['entry_price']) / df['entry_price']) * 100
            df['pl_abs'] = (df['current_price'] - df['entry_price'])
        else:
            # Filter resulted in empty dataframe
            pass
    else:
        # Database is empty
        pass

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["🔭 Live Market Monitor", "💼 The $100k Challenge", "🏆 The 90-Day Truth"])

# === Tab 1: Live Market Monitor ===
with tab1:
    if df.empty:
        st.info("ℹ️ No active signals match your filters. Waiting for the Sniper to find targets...")
    else:
        # KPIs
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Active Signals", len(df))
        with col2:
            avg_return = df['pl_pct'].mean()
            st.metric("Avg Return", f"{avg_return:.2f}%", delta=f"{avg_return:.2f}%")
        with col3:
            # Placeholder for sector
            st.metric("Top Sector", "Tech (Est.)")
            
        # Main Table
        st.subheader("📡 Live Signal Feed")
        
        # Configure columns
        column_config = {
            "ticker": "Ticker",
            "confidence_score": st.column_config.NumberColumn("Score", format="%d"),
            "entry_price": st.column_config.NumberColumn("Entry", format="$%.2f"),
            "current_price": st.column_config.NumberColumn("Current", format="$%.2f"),
            "pl_pct": st.column_config.NumberColumn(
                "P/L %", 
                format="%.2f%%",
            ),
            "created_at": st.column_config.DatetimeColumn("Found At", format="D MMM, h:mm a"),
        }
        
        display_cols = ["ticker", "confidence_score", "entry_price", "current_price", "pl_pct", "created_at"]
        
        # Use data_editor for cleaner look, disabled editing
        # Apply styling: We can't easily do row-based styling in data_editor yet without pandas styler
        # But pandas styler works with st.dataframe
        
        def highlight_pl(val):
            color = 'red' if val < 0 else 'green'
            return f'color: {color}'

        st.dataframe(
            df[display_cols].sort_values("created_at", ascending=False).style.map(highlight_pl, subset=['pl_pct']),
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            height=500
        )

# === Tab 2: The $100k Challenge ===
with tab2:
    st.header("💼 Paper Trading Simulation ($100k)")
    st.caption("Allocating $10,000 to top 10 newest signals with Score > 80")
    
    if df.empty:
        st.info("💼 Portfolio is empty. Waiting for high-score signals...")
    else:
        # Logic: Filter > 80, Sort by Newest, Take top 10
        portfolio_df = df[df['confidence_score'] > 80].sort_values("created_at", ascending=False).head(10).copy()
        
        if portfolio_df.empty:
            st.info("💼 No high-confidence signals (>80) available for portfolio construction yet.")
        else:
            # Allocation
            ALLOCATION_PER_STOCK = 10000
            portfolio_df['shares'] = ALLOCATION_PER_STOCK / portfolio_df['entry_price']
            portfolio_df['position_value'] = portfolio_df['shares'] * portfolio_df['current_price']
            portfolio_df['profit'] = portfolio_df['position_value'] - ALLOCATION_PER_STOCK
            
            # Totals
            invested_capital = len(portfolio_df) * ALLOCATION_PER_STOCK
            cash = 100000 - invested_capital
            total_value = cash + portfolio_df['position_value'].sum()
            total_profit = total_value - 100000
            
            # Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("Portfolio Value", f"${total_value:,.2f}", delta=f"${total_profit:,.2f}")
            m2.metric("Cash", f"${cash:,.2f}")
            m3.metric("Invested", f"${invested_capital:,.2f}")
            
            # Charts
            c1, c2 = st.columns([1, 2])
            with c1:
                # Pie Chart
                fig = px.pie(portfolio_df, values='position_value', names='ticker', title='Allocation', hole=0.4)
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
                st.plotly_chart(fig, use_container_width=True)
                
            with c2:
                # Performance Bar Chart
                fig2 = px.bar(
                    portfolio_df, 
                    x='ticker', 
                    y='profit', 
                    color='profit',
                    title='Profit/Loss by Position',
                    color_continuous_scale=['red', 'green']
                )
                fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
                st.plotly_chart(fig2, use_container_width=True)

# === Tab 3: The 90-Day Truth ===
with tab3:
    st.header("🏆 Long Term Validation")
    
    if df.empty:
        st.warning("⏳ System is too new. Data will populate in 3 months.")
    else:
        # Filter for signals > 90 days old
        ninety_days_ago = datetime.now() - timedelta(days=90)
        
        # Ensure created_at is datetime
        old_df = df[df['created_at'] < ninety_days_ago]
        
        if old_df.empty:
            st.warning("⏳ System is too new for 90-day validation. Data is accumulating...")
            if not df.empty:
                oldest_date = df['created_at'].min().strftime('%Y-%m-%d')
                st.caption(f"Oldest signal found: {oldest_date} (Need 90 days history)")
        else:
            # Calculate Win Rate (Positive Return)
            wins = old_df[old_df['pl_pct'] > 0]
            win_rate = (len(wins) / len(old_df)) * 100
            
            st.metric("Win Rate (90 Days)", f"{win_rate:.1f}%")
            
            # Gauge Chart
            fig = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = win_rate,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Win Rate"},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "lightgreen" if win_rate > 50 else "red"},
                    'steps': [
                        {'range': [0, 50], 'color': "gray"},
                        {'range': [50, 100], 'color': "darkgray"}],
                }
            ))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig)
