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
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.shared import JsCode

# Add parent dir to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard_utils import load_css, check_password, init_clients

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

    # --- MAIN TABLE (AgGrid is fine for Legacy Data) ---
    st.markdown("### 📋 Database Records")
    
    display_df = filtered_df[['ticker', 'created_at', 'entry_price', 'current_price', 'confidence_score', 'status', 's_hunter']].copy()
    display_df.columns = ['Ticker', 'Date', 'Entry', 'Current', 'Score', 'Status', 'Hunter']
    
    # Format
    display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    display_df['Score'] = display_df['Score'].round(1)
    
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_selection('single', use_checkbox=False)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=15)
    
    # Style Score
    gb.configure_column("Score", cellStyle={'fontWeight': 'bold'})
    
    grid_response = AgGrid(
        display_df, 
        gridOptions=gb.build(), 
        height=500, 
        theme='balham',
        allow_unsafe_jscode=True
    )
    
    # --- INSPECTOR ---
    selection = grid_response['selected_rows']
    if selection is not None and not isinstance(selection, int) and len(selection) > 0:
        if isinstance(selection, pd.DataFrame):
             selected_ticker = selection.iloc[0]['Ticker']
        elif isinstance(selection, list):
             item = selection[0]
             selected_ticker = item.get('Ticker')
        else:
             selected_ticker = None
             
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
                st.info(f"**Reasons:**\n\n{row.get('reasons', 'N/A')}")
                with st.expander("Raw JSON Data"):
                    st.json(row.get('raw_features', {}))

else:
    st.info("No legacy data found.")
