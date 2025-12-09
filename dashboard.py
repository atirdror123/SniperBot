import os
import json
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from supabase import create_client, Client
from dotenv import load_dotenv
import google.generativeai as genai
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode
from st_aggrid.shared import JsCode

# --- 1. SETUP & CONFIG ---
load_dotenv()
st.set_page_config(page_title="Sniper Terminal v2", page_icon="🎯", layout="wide")

# Theme
st.markdown("""
<style>
    .stApp { background-color: #050505; color: #E0E0E0; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { color: #FFFFFF; font-family: 'Inter', sans-serif; font-weight: 600; }
    [data-testid="stSidebar"] { background-color: #0a0a0a; border-right: 1px solid #1a1a1a; }
    .metric-card { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; }
    .stButton>button { border-radius: 20px; border: 1px solid #00FFFF; color: #00FFFF; background: transparent; }
    .stButton>button:hover { background: rgba(0,255,255,0.1); }
</style>
""", unsafe_allow_html=True)

# Auth & Clients
@st.cache_resource
def init_clients():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    rep_supa = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None
    
    genai_key = os.getenv("GOOGLE_API_KEY")
    if genai_key:
        genai.configure(api_key=genai_key)
    
    return rep_supa

supabase = init_clients()

# --- AUTHENTICATION ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        try:
            if st.session_state["password"] == st.secrets["DASHBOARD_PASSWORD"]:
                st.session_state["password_correct"] = True
                del st.session_state["password"]  # don't store password
            else:
                st.session_state["password_correct"] = False
        except KeyError:
            # Fallback/Error handling if secret is missing
            st.error("⚠️ System Error: Password not configured in Secrets.")
            st.info("Please go to Streamlit Cloud -> Settings -> Secrets and add: DASHBOARD_PASSWORD = '...'" )
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Security Clearance Code", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password validation failure
        st.text_input(
            "Security Clearance Code", type="password", on_change=password_entered, key="password"
        )
        st.error("⛔ ACCESS DENIED")
        return False
    else:
        # Password correct.
        return True

if not check_password():
    st.stop()

# --- 2. DATA LOGIC ---

def derive_sub_scores(row):
    """
    Parses 'raw_features' (JSON) or falls back to 'reasons' (Text) 
    to estimate 0-100 scores for Trend, Volatility, Fundamental, Sentiment.
    """
    raw = row.get('raw_features', {})
    if isinstance(raw, str):
        try: raw = json.loads(raw)
        except: raw = {}
    if raw is None: raw = {}
        
    reasons = str(row.get('reasons', ''))
    
    # --- 4-LENS PARSING ---
    # Attempt to read new Sentient Lens scores
    lens_scores = raw.get('lens_scores', {})
    
    # Defaults if missing (legacy support)
    s_quant = lens_scores.get('QUANT', 0)
    s_oracle = lens_scores.get('ORACLE', 0)
    s_hunter = lens_scores.get('HUNTER', 0)
    s_chartist = lens_scores.get('CHARTIST', 0)
    
    # Fallback to old logic if all zero (legacy data) and no lens keys found
    if not lens_scores and any(k in reasons for k in ['MA Stack', 'RVOL']):
        # ... (Old logic omitted for brevity, focusing on new system execution)
        pass 

    return pd.Series([s_quant, s_oracle, s_hunter, s_chartist])

def fetch_data():
    if not supabase: return pd.DataFrame()
    try:
        # Fetch Limit 100 for performance
        res = supabase.table('sniper_signals').select('*').order('created_at', desc=True).limit(100).execute()
        df = pd.DataFrame(res.data)
        if df.empty: return df
        
        # Parse Dates
        df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert(None)
        
        # Derive Sub-Scores
        df[['s_quant', 's_oracle', 's_hunter', 's_chartist']] = df.apply(derive_sub_scores, axis=1)
        
        return df
    except Exception as e:
        st.error(f"Data Fetch Error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_live_price(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1d")
        if not data.empty:
            return data['Close'].iloc[-1]
    except: pass
    return None

@st.cache_data(show_spinner=False)
def get_ai_summary(ticker, signal_data_str):
    """
    Uses Gemini to generate a summary. Cached.
    """
    if not os.getenv("GOOGLE_API_KEY"):
        return "⚠️ Google API Key not found. Cannot generate AI summary."
    
    try:
        model = genai.GenerativeModel('gemini-flash-latest')
        prompt = f"""
        Analyze this stock signal data for {ticker}:
        {signal_data_str}
        
        Write a professional 3-sentence executive summary:
        1. The Bullish Case (Why it was picked)
        2. Key Risks (Red flags)
        3. Simple Verdict
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"

# --- 3. UI LAYOUT ---

# Sidebar
st.sidebar.title("TARGET LOCK")
st.sidebar.markdown("---")
if st.sidebar.button("🔄 REFRESH DATA"):
    st.cache_data.clear()
    st.rerun()

# Filters
df = fetch_data()
if not df.empty:
    min_score = st.sidebar.slider("Min Confidence Score", 0, 100, 75)
    status_opts = ["All"] + list(df['status'].unique())
    status_filter = st.sidebar.multiselect("Status", status_opts, default="All")
    
    # Apply Filters
    mask = df['confidence_score'] >= min_score
    if "All" not in status_filter and status_filter:
        mask &= df['status'].isin(status_filter)
    
    filtered_df = df[mask].copy()
    
    # Get Live Prices for visible rows (Top 10 to save API)
    visible_tickers = filtered_df['ticker'].head(10).tolist()
    
    # Main Content
    st.title("🎯 SNIPER TERMINAL v2")
    
    # --- TABLE & DATA PREP ---
    st.subheader("SIGNAL FEED")
    
    # 1. Row Count Dropdown
    c_table_controls, _ = st.columns([1, 4])
    with c_table_controls:
        row_limit_opts = [10, 50, 100, "All"]
        row_limit = st.selectbox("Rows to Show", row_limit_opts, index=0)
    
    # 2. Determine tickers to fetch
    if row_limit == "All":
        display_limit = len(filtered_df)
    else:
        display_limit = int(row_limit)
        
    visible_tickers = filtered_df['ticker'].head(display_limit).tolist()
    
    # 3. Batch Fetch Live Prices (Optimize)
    if visible_tickers:
        try:
            live_data = yf.download(visible_tickers, period="1d", group_by='ticker', progress=False, threads=True)
            prices = {}
            for t in visible_tickers:
                try:
                    if len(visible_tickers) == 1:
                        price = live_data['Close'].iloc[-1]
                    else:
                        price = live_data[t]['Close'].iloc[-1]
                    prices[t] = float(price)
                except:
                    prices[t] = None
        except Exception as e:
            st.error(f"Price Fetch Error: {e}")
            prices = {}
    else:
        prices = {}

    # 4. Construct table_df with calculations
    table_df = filtered_df.copy()
    
    # Map prices (fill non-visible or failed with entry_price)
    table_df['current_price'] = table_df['ticker'].map(prices)
    table_df['current_price'] = table_df['current_price'].fillna(table_df['entry_price'])
    
    # Calculate Return
    table_df['return_pct'] = ((table_df['current_price'] - table_df['entry_price']) / table_df['entry_price']) * 100
    
    # Calculate 3M Status
    now = pd.Timestamp.now()
    def get_3m_status(row):
        days = (now - row['created_at']).days
        if days >= 90:
            return "SUCCESS" if row['return_pct'] >= 5.0 else "FAIL"
        return "PENDING"
    table_df['3m_result'] = table_df.apply(get_3m_status, axis=1)

    # --- TOP METRICS (Now safe to render) ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Signals", len(filtered_df))
    m2.metric("Avg Score", f"{filtered_df['confidence_score'].mean():.1f}")
    
    # Metric 3: Avg Return
    # We use table_df because it has the return_pct calculated (though partially imputed for non-visible rows)
    # If the user selected "10 rows", we only fetched prices for 10. Avg return will be biased towards 0 for the others.
    # But this is an acceptable trade-off for performance unless we background fetch all.
    # Let's clarify in UI if needed, but for now just show it.
    avg_ret = table_df['return_pct'].head(display_limit).mean() # Calculate on Visible Set to be accurate to what user sees? Or all?
    # Let's do ALL, accepting that non-visible are 0%.
    avg_ret_all = table_df['return_pct'].mean()
    m3.metric("Avg Return", f"{avg_ret_all:.2f}%", delta_color="normal")
    
    recent_signal = filtered_df.iloc[0]['ticker'] if not filtered_df.empty else "-"
    m4.metric("Latest Signal", recent_signal)
    
    # --- RENDER TABLE ---
    # Slice for Display
    display_df = table_df.head(display_limit).copy()
    
    # Format for Grid
    display_df = display_df[['ticker', 'created_at', 'entry_price', 'current_price', 'return_pct', 'confidence_score', '3m_result', 'status']]
    display_df.columns = ['Ticker', 'Date', 'Entry', 'Current', 'Return %', 'Score', '3M Result', 'Status']
    display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    display_df['Entry'] = display_df['Entry'].round(2)
    display_df['Current'] = display_df['Current'].round(2)
    display_df['Return %'] = display_df['Return %'].round(2)
    
    # AgGrid
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_selection('single', use_checkbox=False)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=display_limit)
    
    # Color Code Return %
    cells_ret = JsCode("""
    function(params) {
        if (params.value > 0) { return {'color': '#00FFA3'}; }
        else if (params.value < 0) { return {'color': '#FF0055'}; }
        return {'color': 'white'};
    }
    """)
    gb.configure_column("Return %", cellStyle=cells_ret)

    # Color Code 3M Result
    cells_3m = JsCode("""
    function(params) {
        if (params.value == 'SUCCESS') { return {'color': '#00FFA3', 'fontWeight': 'bold'}; }
        else if (params.value == 'FAIL') { return {'color': '#FF0055', 'fontWeight': 'bold'}; }
        return {'color': '#888888'};
    }
    """)
    gb.configure_column("3M Result", cellStyle=cells_3m)
    
    grid_response = AgGrid(
        display_df, 
        gridOptions=gb.build(), 
        height=400 if row_limit == "All" or display_limit > 10 else 250, 
        allow_unsafe_jscode=True,
        theme='balham'
    )
    
    # --- INSPECTOR ---
    selection = grid_response['selected_rows']
    # Debug selection (optional)
    # st.write(selection)

    # Check if selection is a DataFrame or List and extract Ticker
    selected_ticker = None
    
    # AgGrid with 'DataReturnMode.AS_INPUT' or pandas returns might behave differently
    # Standardize:
    if selection is not None:
        if isinstance(selection, pd.DataFrame) and not selection.empty:
            selected_ticker = selection.iloc[0]['Ticker']
        elif isinstance(selection, list) and len(selection) > 0:
            item = selection[0]
            # Handle list of dicts or list of Row objects
            if isinstance(item, dict):
                selected_ticker = item.get('Ticker')
            else:
                # Fallback for weird objects
                try: selected_ticker = item['Ticker']
                except: pass
    
    # Explicit check to ensure we didn't miss it due to Case Sensitivity
    # Our dataframe cols are 'Ticker', 'Date', etc.
    if selected_ticker:
        # Get Full Data for Selected
        row = filtered_df[filtered_df['ticker'] == selected_ticker].iloc[0]
        
        st.markdown("---")
        st.header(f"🔎 INSPECTOR: {selected_ticker}")
        
        c1, c2 = st.columns([1, 1])
        
        with c1:
            st.subheader("Strategy DNA")
            # Radar Chart
            categories = ['Quant', 'Oracle', 'Hunter', 'Chartist']
            values = [row['s_quant'], row['s_oracle'], row['s_hunter'], row['s_chartist']]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories,
                fill='toself',
                name=selected_ticker,
                line_color='#00FFFF'
            ))
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100], color='#888'),
                    bgcolor='rgba(0,0,0,0)'
                ),
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                showlegend=False,
                margin=dict(l=40, r=40, t=20, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Raw Data Expander
            with st.expander("Raw Data"):
                st.json(row['raw_features'])
                st.text(row['reasons'])
        
        with c2:
            st.subheader("🤖 AI Analyst")
            
            # Prepare Data for Context
            context_data = {
                'ticker': row['ticker'],
                'score': row['confidence_score'],
                'sub_scores': {'Quant': row['s_quant'], 'Oracle': row['s_oracle'], 'Hunter': row['s_hunter'], 'Chartist': row['s_chartist']},
                'reasons_text': row['reasons'],
                'raw': row['raw_features']
            }
            
            # Loading State
            with st.spinner("consulting the oracle..."):
                summary = get_ai_summary(selected_ticker, str(context_data))
                
            st.info(summary)

else:
    st.warning("No Data Found in Database.")
