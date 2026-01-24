"""
Legacy Database Page
Shows the original 175 stocks mined in Phase 0.
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
st.set_page_config(page_title="Legacy Database", page_icon="🗄️", layout="wide")
load_css()

if not check_password():
    st.stop()

supabase = init_clients()

st.title("🗄️ Legacy Database (175 Stocks)")
st.markdown("Original V1.0 mining results. These stocks are being tracked for historical analysis.")

# --- FETCH DATA ---
@st.cache_data(ttl=600)
def fetch_legacy_data():
    if not supabase: return pd.DataFrame()
    try:
        # Fetch all legacy stocks
        res = supabase.table('sniper_signals').select('*').limit(500).execute()
        df = pd.DataFrame(res.data)
        if df.empty: return df
        
        # Parse Dates
        df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert(None)
        
        # Sub-scores function (local copy to avoid complex imports)
        def derive_sub_scores(row):
            raw = row.get('raw_features', {})
            if isinstance(raw, str):
                try: raw = json.loads(raw)
                except: raw = {}
            if raw is None: raw = {}
            
            reasons = str(row.get('reasons', ''))
            lens_scores = raw.get('lens_scores', {})
            
            s_quant = lens_scores.get('QUANT', 0)
            s_oracle = lens_scores.get('ORACLE', 0)
            s_hunter = lens_scores.get('HUNTER', 0)
            s_chartist = lens_scores.get('CHARTIST', 0)
            return pd.Series([s_quant, s_oracle, s_hunter, s_chartist])

        df[['s_quant', 's_oracle', 's_hunter', 's_chartist']] = df.apply(derive_sub_scores, axis=1)
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

df = fetch_legacy_data()

try:
    if not df.empty:
        # --- FILTERS ---
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown("### Filters")
            status_opts = ["All"] + list(df['status'].unique())
            status_filter = st.selectbox("Status", status_opts, index=0)
            
        # Filter Logic
        filtered_df = df.copy()
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df['status'] == status_filter]
    
        # --- BATCH FETCH LIVE PRICES ---
        # Initialize current_price with entry_price as fallback
        if 'current_price' not in filtered_df.columns or filtered_df['current_price'].isna().all():
            filtered_df['current_price'] = filtered_df['entry_price']
        
        # Fetch prices for filtered items to show real-time stats
        tickers = filtered_df['ticker'].unique().tolist()
        if tickers:
            try:
                # Optimized batch download
                data = yf.download(tickers, period="1d", group_by='ticker', progress=False, threads=True)
                
                if not data.empty:
                    def get_price_from_batch(t, batch_data):
                        try:
                            if len(tickers) == 1:
                                return float(batch_data['Close'].iloc[-1])
                            return float(batch_data[t]['Close'].iloc[-1])
                        except:
                            return None
                    
                    # Update current_price with live data
                    for t in tickers:
                        price = get_price_from_batch(t, data)
                        if price is not None:
                            filtered_df.loc[filtered_df['ticker'] == t, 'current_price'] = price
                
            except Exception as e:
                st.warning(f"Live Price warning: {e}")

        # --- MAIN TABLE ---
        st.markdown("### 📋 Database Records (Live Prices)")
        
        # Ensure columns exist
        cols = ['ticker', 'created_at', 'entry_price', 'confidence_score', 'status', 's_hunter']
        if 'current_price' in filtered_df.columns:
            cols.insert(3, 'current_price')
        else:
            filtered_df['current_price'] = filtered_df['entry_price']
            cols.insert(3, 'current_price')

        display_df = filtered_df[cols].copy()
        
        # Calculate Change %
        display_df['change_pct'] = ((display_df['current_price'] - display_df['entry_price']) / display_df['entry_price']) * 100
        
        # Rename safely
        display_df.rename(columns={
            'ticker': 'Ticker', 
            'created_at': 'Date', 
            'entry_price': 'Entry', 
            'current_price': 'Current', 
            'confidence_score': 'Score', 
            'status': 'Status', 
            's_hunter': 'Hunter',
            'change_pct': 'Change %'
        }, inplace=True)
        
        # Reorder for display
        display_df = display_df[['Ticker', 'Date', 'Entry', 'Current', 'Change %', 'Score', 'Status', 'Hunter']]
        
        # Format
        display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
        display_df['Score'] = display_df['Score'].round(1)
        display_df['Change %'] = display_df['Change %'].round(2)
        display_df['Entry'] = display_df['Entry'].round(2)
        display_df['Current'] = display_df['Current'].round(2)
        
        gb = GridOptionsBuilder.from_dataframe(display_df)
        gb.configure_selection('single', use_checkbox=False)
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
        
        # Style Score & Change
        gb.configure_column("Score", cellStyle={'fontWeight': 'bold'})
        
        # Color Code Change %
        cells_ret = JsCode("""
        function(params) {
            if (params.value > 0) { return {'color': '#00873C', 'fontWeight': 'bold'}; }
            else if (params.value < 0) { return {'color': '#EB0029', 'fontWeight': 'bold'}; }
            return {'color': '#333'};
        }
        """)
        gb.configure_column("Change %", cellStyle=cells_ret)
        
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
                    # Radar Chart
                    categories = ['Quant', 'Oracle', 'Hunter', 'Chartist']
                    values = [row['s_quant'], row['s_oracle'], row['s_hunter'], row['s_chartist']]
                    categories = [*categories, categories[0]]
                    values = [*values, values[0]]
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=categories,
                        fill='toself',
                        name=selected_ticker,
                        line_color='#6200EA'
                    ))
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 100]),
                        ),
                        margin=dict(l=40, r=40, t=20, b=20),
                        height=300
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with c2:
                    st.subheader("🤖 AI Analyst")
                    
                    # Prepare context
                    context = {
                        'ticker': selected_ticker,
                        'score': row['confidence_score'],
                        'features': row.get('raw_features', {}),
                        'raw_reason': row.get('reasons', '')
                    }
                    
                    if st.button("🧠 Generate AI Analysis"):
                        with st.spinner("Consulting the Oracle..."):
                            summary = get_ai_summary(selected_ticker, str(context))
                        st.info(summary)
                    else:
                        st.info("Click button to generate fresh analysis.")
                        with st.expander("Show Raw Data"):
                            st.json(row.get('raw_features', {}))
                            st.text(row.get('reasons', ''))
    
    else:
        st.info("No legacy data found.")
        
except Exception as e:
    st.error("⚠️ An error occurred while rendering the page:")
    st.exception(e)
