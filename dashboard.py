"""
🎯 SNIPER TERMINAL V2
Home Page - Focuses on the new Sniper V2.0 System.
"""
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import yfinance as yf
from dashboard_utils import load_css, check_password, init_clients, fetch_system_status, get_live_price

# --- CONFIG ---
st.set_page_config(page_title="Sniper Terminal", page_icon="🎯", layout="wide")
load_css()

if not check_password():
    st.stop()

supabase = init_clients()

# --- SIDEBAR ---
# Just simple status, no filters needed for main view usually
status = fetch_system_status(supabase)
st.sidebar.title("TARGET LOCK")
if status == "RUNNING":
    st.sidebar.success("🟢 SCANNING ACTIVE")
else:
    st.sidebar.info(f"⚪ STATUS: {status}")

if st.sidebar.button("🔄 REFRESH"):
    st.rerun()

# --- FETCH DATA ---
@st.cache_data(ttl=60)
def fetch_home_data():
    if not supabase: return None, pd.DataFrame(), pd.DataFrame()
    try:
        # Portfolio Config
        p_res = supabase.table("portfolio_config").select("*").eq("id", "SNIPER").execute()
        portfolio = p_res.data[0] if p_res.data else None
        
        # Open Positions - READ FROM sniper_signals (where run_scanner.py writes!)
        # The scanner saves signals with status='OPEN', so we query that
        pos_res = supabase.table("sniper_signals").select("*").eq("status", "OPEN").order("created_at", desc=True).execute()
        open_df = pd.DataFrame(pos_res.data) if pos_res.data else pd.DataFrame()
        
        # Map column names: sniper_signals uses different names than paper_positions
        if not open_df.empty:
            # Ensure we have required columns for dashboard display
            if 'confidence_score' in open_df.columns and 'quantity' not in open_df.columns:
                # Default quantity = 1 for now (signal, not position tracking)
                open_df['quantity'] = 1
        
        # Equity History
        eq_res = supabase.table("equity_history").select("*").eq("portfolio", "SNIPER").order("recorded_at").execute()
        equity_df = pd.DataFrame(eq_res.data) if eq_res.data else pd.DataFrame()
        
        return portfolio, open_df, equity_df
    except Exception as e:
        print(f"Dashboard data fetch error: {e}")
        return None, pd.DataFrame(), pd.DataFrame()

portfolio, open_df, equity_df = fetch_home_data()

# --- HEADER SECTION ---
st.title("🎯 Sniper Terminal")
st.markdown(f"**V2.0 Active** | Market Regime: **BULL** (Simulated)")

# --- 1. HERO METRICS ---
if portfolio:
    c1, c2, c3, c4 = st.columns(4)
    
    starting = portfolio.get('starting_capital', 100000)
    current = portfolio.get('current_equity', 100000)
    pnl = current - starting
    pnl_pct = (pnl / starting) * 100
    
    # Calculate daily change (mock for now or last equity point)
    daily_change = 0 # Placeholder
    
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Current Equity</div>
            <div class="metric-value">${current:,.0f}</div>
            <div class="metric-delta delta-pos">{pnl_pct:+.2f}% Overall</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Day Change</div>
            <div class="metric-value">$0</div>
            <div class="metric-delta">0.00%</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c3:
        open_pos_count = len(open_df) if not open_df.empty else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Open Positions</div>
            <div class="metric-value">{open_pos_count}</div>
            <div class="metric-delta">Max 3/Day</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
         st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Cash Balance</div>
            <div class="metric-value">${(current - (open_pos_count * 2000)):,.0f}</div>
            <div class="metric-delta">Ready to Deploy</div>
        </div>
        """, unsafe_allow_html=True)

# --- 2. EQUITY CURVE ---
if not equity_df.empty:
    st.markdown("### 📈 Performance Curve")
    equity_df['recorded_at'] = pd.to_datetime(equity_df['recorded_at'])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity_df['recorded_at'],
        y=equity_df['equity'],
        mode='lines',
        name='Equity',
        line=dict(color='#0052FF', width=3),
        fill='tozeroy',
        fillcolor='rgba(0, 82, 255, 0.1)'
    ))
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=0, r=0, t=10, b=0),
        height=300,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#F0F0F0')
    )
    st.plotly_chart(fig, use_container_width=True)


# --- 3. LIVE POSITIONS (Modern HTML Table) ---
st.markdown("### 📂 Active Sniper Positions")

if not open_df.empty:
    # Fetch live prices
    tickers = open_df['ticker'].tolist()
    live_prices = {}
    
    # Batch fetch is better but for <10 stocks loop is fine too
    for t in tickers:
        p = get_live_price(t)
        if p: live_prices[t] = p
    
    # Build HTML Table
    table_html = """
    <table class="sniper-table">
        <thead>
            <tr>
                <th>Ticker</th>
                <th>Entry Date</th>
                <th>Entry Price</th>
                <th>Current Price</th>
                <th>Qty</th>
                <th>Return</th>
                <th>Value</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for _, row in open_df.iterrows():
        ticker = row['ticker']
        entry = row['entry_price']
        qty = row['quantity']
        curr = live_prices.get(ticker, entry)
        
        ret_pct = ((curr - entry) / entry) * 100
        val = curr * qty
        
        # Color badge
        color_class = "badge-green" if ret_pct >= 0 else "badge-red"
        ret_str = f"{ret_pct:+.2f}%"
        
        table_html += f"""
        <tr>
            <td style="font-weight:600">{ticker}</td>
            <td>{pd.to_datetime(row['created_at']).strftime('%Y-%m-%d')}</td>
            <td>${entry:.2f}</td>
            <td>${curr:.2f}</td>
            <td>{qty}</td>
            <td><span class="badge {color_class}">{ret_str}</span></td>
            <td style="font-weight:600">${val:,.2f}</td>
        </tr>
        """
        
    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)
    
else:
    st.info("No active positions. Waiting for next scan...")

# --- 4. AI LENS BREAKDOWN ---
st.markdown("### 🔬 AI Lens Analysis")

if not open_df.empty:
    # Check if we have AI scores in raw_features
    has_ai_scores = False
    for _, row in open_df.iterrows():
        raw_features = row.get('raw_features', {})
        if isinstance(raw_features, dict) and 'ai_scores' in raw_features:
            has_ai_scores = True
            break
    
    if has_ai_scores:
        for _, row in open_df.iterrows():
            ticker = row['ticker']
            raw_features = row.get('raw_features', {})
            ai_scores = raw_features.get('ai_scores', {}) if isinstance(raw_features, dict) else {}
            
            if ai_scores:
                with st.expander(f"📊 {ticker} - AI Scoring Breakdown"):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        hunter = ai_scores.get('hunter', 0)
                        st.metric("🎯 HUNTER", f"{hunter}/100", 
                                 help="Insider trading sentiment analysis")
                    
                    with col2:
                        quant = ai_scores.get('quant', 0)
                        st.metric("📊 QUANT", f"{quant}/100",
                                 help="Institutional ownership quality")
                    
                    with col3:
                        oracle = ai_scores.get('oracle', 0)
                        st.metric("🔮 ORACLE", f"{oracle}/100",
                                 help="AI synthesis and prediction")
                    
                    with col4:
                        final = ai_scores.get('final', 0)
                        st.metric("⭐ FINAL", f"{final}/100",
                                 help="Weighted composite score")
                    
                    # Visual breakdown
                    st.markdown("**Score Composition:**")
                    fig = go.Figure(data=[
                        go.Bar(
                            x=['Hunter (40%)', 'Quant (30%)', 'Oracle (30%)'],
                            y=[hunter * 0.4, quant * 0.3, oracle * 0.3],
                            marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1'],
                            text=[f"{hunter * 0.4:.1f}", f"{quant * 0.3:.1f}", f"{oracle * 0.3:.1f}"],
                            textposition='auto'
                        )
                    ])
                    fig.update_layout(
                        showlegend=False,
                        height=200,
                        margin=dict(l=0, r=0, t=0, b=0),
                        yaxis_title="Contribution to Final Score"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Tournament rank if available
                    tournament_rank = raw_features.get('tournament_rank')
                    if tournament_rank:
                        st.info(f"🏆 Tournament Rank: #{tournament_rank}")
    else:
        st.info("💡 AI scoring data not available for current positions. Run a new scan to see AI lens analysis.")
else:
    st.info("No positions to analyze.")

# --- 5. RECENT SIGNALS (Today's Candidates) ---
st.markdown("### 📡 Latest Signals (Paper Trading Queue)")
# Fetch recent paper positions that are PENDING or OPEN created in last 24h
# For now just show "No new signals" visual placeholder if empty
if open_df.empty:
     st.markdown("""
        <div style="background: #F9F9F9; padding: 30px; border-radius: 10px; text-align: center; border: 1px dashed #ccc;">
            <p style="color: #888;">📡 Scanner is idle. Next scan at 14:45 UTC.</p>
        </div>
     """, unsafe_allow_html=True)
