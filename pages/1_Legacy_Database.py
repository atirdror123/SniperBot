"""
Legacy Database Page (V2 - Hard Separation)
Shows the legacy portfolio data from legacy_portfolio table.
"""
import sys
import os
import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.shared import JsCode

# Add parent dir to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard_utils import load_css, check_password, init_clients, get_ai_summary

# --- CONFIG ---
st.set_page_config(page_title="Legacy Archive", page_icon="🏛️", layout="wide")
load_css()

if not check_password():
    st.stop()

supabase = init_clients()

st.title("🏛️ Legacy Archive")
st.markdown("Original V1.0 positions. This data is **frozen** - no automated trading.")

# --- FETCH DATA FROM legacy_portfolio ---
@st.cache_data(ttl=300)
def fetch_legacy_data():
    if not supabase: return pd.DataFrame()
    try:
        # Fetch from legacy_portfolio (Hard Separation table)
        res = supabase.table('legacy_portfolio').select('*').execute()
        df = pd.DataFrame(res.data)
        if df.empty: return df
        
        # Parse Dates
        if 'entry_date' in df.columns:
            df['entry_date'] = pd.to_datetime(df['entry_date']).dt.tz_convert(None)
        elif 'created_at' in df.columns:
            df['entry_date'] = pd.to_datetime(df['created_at']).dt.tz_convert(None)
        
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

df = fetch_legacy_data()

try:
    if not df.empty:
        # ============================================
        # FIX: Count from the SAME DataFrame (exact match)
        # ============================================
        total_count = len(df)
        open_count = len(df[df['status'] == 'OPEN']) if 'status' in df.columns else 0
        closed_count = len(df[df['status'] == 'CLOSED']) if 'status' in df.columns else 0
        
        # --- BATCH FETCH LIVE PRICES ---
        if 'current_price' not in df.columns:
            df['current_price'] = df['entry_price']
        
        tickers = df['ticker'].unique().tolist()
        if tickers:
            try:
                data = yf.download(tickers, period="1d", group_by='ticker', progress=False, threads=True)
                
                if not data.empty:
                    def get_price_from_batch(t, batch_data):
                        try:
                            if len(tickers) == 1:
                                return float(batch_data['Close'].iloc[-1])
                            return float(batch_data[t]['Close'].iloc[-1])
                        except:
                            return None
                    
                    for t in tickers:
                        price = get_price_from_batch(t, data)
                        if price is not None:
                            df.loc[df['ticker'] == t, 'current_price'] = price
                
            except Exception as e:
                st.warning(f"Live Price warning: {e}")
        
        # ============================================
        # Calculate Average Return
        # ============================================
        df['change_pct'] = ((df['current_price'] - df['entry_price']) / df['entry_price']) * 100
        avg_return = df['change_pct'].mean() if not df['change_pct'].isna().all() else 0
        
        # --- METRICS ROW ---
        st.markdown("### 📊 Portfolio Summary")
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.metric("Total Positions", total_count)
        with c2:
            st.metric("Open (Frozen)", open_count)
        with c3:
            st.metric("Closed", closed_count)
        with c4:
            # NEW: Average Portfolio Return metric
            st.metric("Avg Portfolio Return", f"{avg_return:+.2f}%")
        
        # --- FILTERS ---
        st.markdown("---")
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown("### Filters")
            status_opts = ["All"] + list(df['status'].unique()) if 'status' in df.columns else ["All"]
            status_filter = st.selectbox("Status", status_opts, index=0)
            
        # Filter Logic
        filtered_df = df.copy()
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['status'] == status_filter]

        # --- MAIN TABLE ---
        st.markdown("### 📋 Legacy Holdings (Live Prices)")
        
        # Prepare display columns
        display_df = filtered_df[['ticker', 'entry_date', 'entry_price', 'current_price', 'change_pct', 'status']].copy()
        
        # Rename safely
        display_df.rename(columns={
            'ticker': 'Ticker', 
            'entry_date': 'Date', 
            'entry_price': 'Entry', 
            'current_price': 'Current', 
            'change_pct': '% Change',
            'status': 'Status'
        }, inplace=True)
        
        # Format
        display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
        display_df['% Change'] = display_df['% Change'].round(2)
        display_df['Entry'] = display_df['Entry'].round(2)
        display_df['Current'] = display_df['Current'].round(2)
        
        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_selection('single', use_checkbox=False)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=20)
        
        # Color Code Change %
        cells_ret = JsCode("""
        function(params) {
            if (params.value > 0) { return {'color': '#00873C', 'fontWeight': 'bold'}; }
            else if (params.value < 0) { return {'color': '#EB0029', 'fontWeight': 'bold'}; }
            return {'color': '#333'};
        }
        """)
        gb.configure_column("% Change", cellStyle=cells_ret)
        
        grid_response = AgGrid(
            display_df, 
            gridOptions=gb.build(), 
            height=500, 
            theme='balham',
            allow_unsafe_jscode=True
        )
        
        # --- INSPECTOR ---
        selection = grid_response['selected_rows']
        if selection is not None:
             selected_ticker = None
             if isinstance(selection, pd.DataFrame) and not selection.empty:
                 selected_ticker = selection.iloc[0]['Ticker']
             elif isinstance(selection, list) and len(selection) > 0:
                 item = selection[0]
                 if isinstance(item, dict):
                     selected_ticker = item.get('Ticker')
                 else:
                     try: selected_ticker = item['Ticker']
                     except: pass
                 
             if selected_ticker:
                row = filtered_df[filtered_df['ticker'] == selected_ticker].iloc[0]
                
                st.markdown("---")
                st.subheader(f"🔍 Inspector: {selected_ticker}")
                
                c1, c2 = st.columns(2)
                
                with c1:
                    st.markdown("**Position Details:**")
                    st.write(f"- Entry Price: ${row['entry_price']:.2f}")
                    st.write(f"- Current Price: ${row['current_price']:.2f}")
                    st.write(f"- Status: {row['status']}")
                    if 'pnl' in row and row['pnl']:
                        st.write(f"- PnL: ${row['pnl']:+,.2f}")
                
                with c2:
                    st.subheader("🤖 AI Analyst")
                    
                    context = {
                        'ticker': selected_ticker,
                        'entry_price': row['entry_price'],
                        'current_price': row['current_price'],
                        'change_pct': row['change_pct']
                    }
                    
                    if st.button("🧠 Generate AI Analysis"):
                        with st.spinner("Consulting the Oracle..."):
                            summary = get_ai_summary(selected_ticker, str(context))
                        st.info(summary)
                    else:
                        st.info("Click button to generate fresh analysis.")

    else:
        st.info("No legacy data found in legacy_portfolio table.")
        
except Exception as e:
    st.error("⚠️ An error occurred while rendering the page:")
    st.exception(e)
