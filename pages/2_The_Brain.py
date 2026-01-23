"""
The Brain - Learning Center
Shows AI self-learning progress, weight evolution, and stats.
"""
import sys
import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dashboard_utils import load_css, check_password, init_clients

# --- CONFIG ---
st.set_page_config(page_title="The Brain", page_icon="🧠", layout="wide")
load_css()

if not check_password():
    st.stop()

supabase = init_clients()

st.title("🧠 The Brain (Self-Learning)")
st.markdown("Tracking the AI's evolution and weight adjustments over time.")

# --- FETCH DATA ---
@st.cache_data(ttl=300)
def fetch_learning_data():
    if not supabase: return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    try:
        # weights
        w_res = supabase.table("lens_weights").select("*").execute()
        w_df = pd.DataFrame(w_res.data) if w_res.data else pd.DataFrame()
        
        # history
        h_res = supabase.table("weight_history").select("*").order("created_at", desc=True).limit(100).execute()
        h_df = pd.DataFrame(h_res.data) if h_res.data else pd.DataFrame()
        
        # outcomes
        o_res = supabase.table("sentient_memory").select("*").execute()
        o_df = pd.DataFrame(o_res.data) if o_res.data else pd.DataFrame()
        
        return w_df, h_df, o_df
    except:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

weights_df, history_df, outcomes_df = fetch_learning_data()

# --- 1. CURRENT WEIGHTS ---
st.subheader("Current Neural Weights")

if not weights_df.empty:
    cols = st.columns(3)
    regime_colors = {'BULL': '#27ae60', 'BEAR': '#c0392b', 'CHOP': '#f39c12'}
    
    for idx, row in weights_df.iterrows():
        regime = row.get('regime', 'N/A')
        color = regime_colors.get(regime, '#888')
        col_idx = idx % 3
        
        with cols[col_idx]:
             st.markdown(f"""
            <div style="background: white; border: 1px solid #eee; border-radius: 10px; padding: 20px; border-top: 4px solid {color}; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                <h3 style="color: {color} !important; margin: 0 0 15px 0;">{regime}</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                    <div><small style='color:#666'>QUANT</small><br><b>{row.get('w_quant', 1.0):.2f}</b></div>
                    <div><small style='color:#666'>ORACLE</small><br><b>{row.get('w_oracle', 1.0):.2f}</b></div>
                    <div><small style='color:#666'>HUNTER</small><br><b style='color:#f1c40f'>{row.get('w_hunter', 1.0):.2f}</b></div>
                    <div><small style='color:#666'>CHARTIST</small><br><b>{row.get('w_chartist', 1.0):.2f}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("No weights found.")

# --- 2. EVOLUTION CHART ---
st.markdown("---")
st.subheader("📈 Weight Evolution")

if not history_df.empty:
    history_df['created_at'] = pd.to_datetime(history_df['created_at'])
    
    fig = go.Figure()
    colors = {'QUANT': '#3498db', 'ORACLE': '#9b59b6', 'HUNTER': '#f1c40f', 'CHARTIST': '#2ecc71'}
    
    for lens in ['w_quant', 'w_oracle', 'w_hunter', 'w_chartist']:
        name = lens.replace('w_', '').upper()
        fig.add_trace(go.Scatter(
            x=history_df['created_at'],
            y=history_df[lens],
            mode='lines+markers',
            name=name,
            line=dict(color=colors.get(name, '#888'), width=2)
        ))
    
    fig.update_layout(
        title="Lens Weight Changes Over Time",
        xaxis_title="Date",
        yaxis_title="Weight Value",
        template="plotly_white",
        height=400,
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No history yet.")

# --- 3. OUTCOME STATS ---
st.markdown("---")
st.subheader("🎯 Outcome Statistics")

if not outcomes_df.empty:
    c1, c2, c3 = st.columns(3)
    
    total = len(outcomes_df)
    c1.metric("Total Tracked", total)
    
    # Calculate Win Rate (simple)
    wins = len(outcomes_df[outcomes_df['outcome_10d'] == 'WIN']) # Just using 10d as proxy
    win_rate = (wins / total * 100) if total > 0 else 0
    c2.metric("10-Day Win Rate", f"{win_rate:.1f}%")
    
    # By Period table
    periods = [10, 20, 30, 40, 50, 60]
    period_data = []
    
    for p in periods:
        col = f"outcome_{p}d"
        if col in outcomes_df.columns:
            w = len(outcomes_df[outcomes_df[col] == 'WIN'])
            l = len(outcomes_df[outcomes_df[col] == 'LOSS'])
            period_data.append({"Period": f"{p} Days", "Wins": w, "Losses": l})
            
    if period_data:
        st.dataframe(pd.DataFrame(period_data), use_container_width=True, hide_index=True)

else:
    st.info("No outcomes tracked yet.")
