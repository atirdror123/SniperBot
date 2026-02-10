"""
🎯 SNIPER TERMINAL V3 - Alpaca Integrated Dashboard
Live Trading Dashboard powered by Alpaca Markets API
"""
import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from dashboard_utils import load_css, check_password, init_clients, fetch_system_status
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
st.set_page_config(page_title="Sniper Terminal", page_icon="🎯", layout="wide")
load_css()

if not check_password():
    st.stop()

supabase = init_clients()
STARTING_CAPITAL = 100000  # Reference point for P/L calculation

# --- ALPACA INTEGRATION ---
@st.cache_resource
def get_alpaca():
    """Initialize Alpaca client if keys are configured."""
    try:
        if os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_SECRET_KEY"):
            from alpaca_client import get_alpaca_client
            return get_alpaca_client()
    except Exception as e:
        st.sidebar.warning(f"Alpaca: {e}")
    return None

alpaca = get_alpaca()

# --- SIDEBAR ---
status = fetch_system_status(supabase)
st.sidebar.title("TARGET LOCK")

if alpaca:
    st.sidebar.success("🟢 ALPACA CONNECTED")
else:
    st.sidebar.warning("⚠️ ALPACA NOT CONFIGURED")
    st.sidebar.caption("Add API keys to .env")

if status == "RUNNING":
    st.sidebar.info("🔄 SCANNING ACTIVE")

if st.sidebar.button("🔄 REFRESH"):
    st.cache_data.clear()
    st.rerun()

# --- HEADER ---
st.title("🎯 Sniper Terminal V3.0")
st.markdown("**Live Trading Dashboard** | Alpaca Paper Trading")

# --- FETCH DATA ---
@st.cache_data(ttl=30)
def fetch_alpaca_data():
    """Fetch live data from Alpaca or fallback to database."""
    if alpaca:
        try:
            account = alpaca.get_account()
            positions = alpaca.get_positions()
            orders = alpaca.get_orders(status="open")
            
            # Build positions DataFrame
            pos_data = []
            for pos in positions:
                pos_data.append({
                    'ticker': pos.symbol,
                    'quantity': int(pos.qty),
                    'entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price),
                    'market_value': float(pos.market_value),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc) * 100,
                    'cost_basis': float(pos.cost_basis)
                })
            
            # Build orders DataFrame
            order_data = []
            for o in orders:
                order_data.append({
                    'ticker': o.symbol,
                    'side': o.side.value.upper(),
                    'qty': int(o.qty) if o.qty else 0,
                    'status': o.status.value.upper(),
                    'submitted': o.submitted_at.strftime("%Y-%m-%d %H:%M")
                })

            return {
                'equity': float(account.equity),
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'positions': pd.DataFrame(pos_data) if pos_data else pd.DataFrame(),
                'orders': pd.DataFrame(order_data) if order_data else pd.DataFrame()
            }
        except Exception as e:
            st.error(f"Alpaca Error: {e}")
    
    # Fallback to database
    return fetch_database_fallback()

def fetch_database_fallback():
    """Fallback to internal database when Alpaca not available."""
    if not supabase:
        return {'equity': STARTING_CAPITAL, 'buying_power': STARTING_CAPITAL, 'cash': STARTING_CAPITAL, 'positions': pd.DataFrame(), 'orders': pd.DataFrame()}
    
    try:
        pos_res = supabase.table("sniper_trades").select("*").eq("status", "OPEN").order("created_at", desc=True).execute()
        open_df = pd.DataFrame(pos_res.data) if pos_res.data else pd.DataFrame()
        
        # Calculate equity from positions
        total_invested = 0
        if not open_df.empty:
            total_invested = open_df.get('invested_amount', open_df.get('entry_price', 0)).sum()
        
        return {
            'equity': STARTING_CAPITAL,  # Static fallback
            'buying_power': STARTING_CAPITAL - total_invested,
            'cash': STARTING_CAPITAL - total_invested,
            'positions': open_df,
            'orders': pd.DataFrame()
        }
    except Exception as e:
        st.error(f"Database Error: {e}")
        return {'equity': STARTING_CAPITAL, 'buying_power': STARTING_CAPITAL, 'cash': STARTING_CAPITAL, 'positions': pd.DataFrame(), 'orders': pd.DataFrame()}

data = fetch_alpaca_data()
positions_df = data['positions']
orders_df = data['orders']

# --- HERO METRICS (NEW LAYOUT) ---
c1, c2, c3, c4 = st.columns(4)

equity = data['equity']
pnl_dollar = equity - STARTING_CAPITAL
pnl_pct = (pnl_dollar / STARTING_CAPITAL) * 100 if STARTING_CAPITAL else 0

with c1:
    delta_class = "delta-pos" if pnl_dollar >= 0 else "delta-neg"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Equity</div>
        <div class="metric-value">${equity:,.2f}</div>
        <div class="metric-delta {delta_class}">Live from Alpaca</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    pnl_color = "delta-pos" if pnl_dollar >= 0 else "delta-neg"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total P/L ($)</div>
        <div class="metric-value {pnl_color}">${pnl_dollar:+,.2f}</div>
        <div class="metric-delta">Since Start</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    pct_color = "delta-pos" if pnl_pct >= 0 else "delta-neg"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total P/L (%)</div>
        <div class="metric-value {pct_color}">{pnl_pct:+.2f}%</div>
        <div class="metric-delta">Overall Return</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    buying_power = data['buying_power']
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Buying Power</div>
        <div class="metric-value">${buying_power:,.2f}</div>
        <div class="metric-delta">Available Cash</div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# SECTION 1: ACTIVE POSITIONS TABLE
# =============================================================================
trade_count = len(positions_df) if not positions_df.empty else 0
st.markdown(f"### 📂 Active Positions ({trade_count})")

if not positions_df.empty:
    # Build display table
    table_rows = []
    
    for _, row in positions_df.iterrows():
        ticker = row['ticker']
        qty = row.get('quantity', row.get('qty', 1)) or 1
        entry = row.get('entry_price', row.get('avg_entry_price', 0)) or 0
        current = row.get('current_price', entry) or entry or 0
        
        # P/L from Alpaca or calculate
        if 'unrealized_pl' in row and row['unrealized_pl'] is not None:
            pnl_dollar = row['unrealized_pl']
            pnl_pct = row.get('unrealized_plpc', 0) or 0
        else:
            pnl_dollar = (current - entry) * qty if current and entry else 0
            invested = entry * qty if entry and qty else 0
            pnl_pct = (pnl_dollar / invested * 100) if invested > 0 else 0
        
        table_rows.append({
            'Ticker': ticker,
            'Qty': qty,
            'Entry': f"${entry:.2f}",
            'Current': f"${current:.2f}",
            'P/L ($)': pnl_dollar,
            'P/L (%)': pnl_pct
        })
    
    display_df = pd.DataFrame(table_rows)
    
    # Format P/L columns with colors
    def style_pnl(val):
        if isinstance(val, (int, float)):
            color = '#00873C' if val >= 0 else '#EB0029'
            return f'color: {color}; font-weight: bold'
        return ''
    
    # Apply formatting
    display_df['P/L ($)'] = display_df['P/L ($)'].apply(lambda x: f"${x:+,.2f}")
    display_df['P/L (%)'] = display_df['P/L (%)'].apply(lambda x: f"{x:+.2f}%")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    if alpaca:
        st.info("📈 No filled positions yet. Check pending orders below.")
    else:
        st.info("🎯 Connect Alpaca API to see live positions.")

# =============================================================================
# SECTION 1.5: PENDING ORDERS (Weekend/After Hours)
# =============================================================================
if not orders_df.empty:
    st.markdown(f"### ⏳ Pending Orders ({len(orders_df)})")
    st.markdown("*(Orders waiting for market open)*")
    
    # Format for display
    order_disp = orders_df.copy()
    order_disp.columns = ['Ticker', 'Side', 'Qty', 'Status', 'Submitted']
    
    st.dataframe(order_disp, use_container_width=True, hide_index=True)

# =============================================================================
# SECTION 2: EQUITY CURVE
# =============================================================================
st.markdown("### 📈 Equity Curve")

@st.cache_data(ttl=60)
def fetch_equity_history():
    if not supabase:
        return pd.DataFrame()
    try:
        eq_res = supabase.table("equity_history").select("*").eq("portfolio", "SNIPER").order("recorded_at").execute()
        return pd.DataFrame(eq_res.data) if eq_res.data else pd.DataFrame()
    except:
        return pd.DataFrame()

equity_df = fetch_equity_history()

if not equity_df.empty:
    equity_df['recorded_at'] = pd.to_datetime(equity_df['recorded_at'])
    
    y_min = equity_df['equity'].min()
    y_max = equity_df['equity'].max()
    y_padding = (y_max - y_min) * 0.1 if y_max != y_min else 5000
    
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
        yaxis=dict(
            showgrid=True, 
            gridcolor='#F0F0F0', 
            title='Total Equity ($)',
            range=[y_min - y_padding, y_max + y_padding]
        )
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("📊 Equity Curve will populate after trades are executed.")

# =============================================================================
# SECTION 3: ACTIVITY LOG
# =============================================================================
st.markdown("### 📋 System Activity Log")

@st.cache_data(ttl=30)
def fetch_activity_logs():
    if not supabase:
        return []
    try:
        res = supabase.table('system_activity_logs').select('*').order('timestamp', desc=True).limit(20).execute()
        return res.data if res.data else []
    except:
        return []

activity_logs = fetch_activity_logs()

if activity_logs:
    log_html = "<div style='background:#FAFAFA; border:1px solid #E0E0E0; border-radius:8px; padding:15px; max-height:200px; overflow-y:auto;'>"
    for log in activity_logs:
        ts = log.get('timestamp', '')[:16].replace('T', ' ')
        action = log.get('action', 'CHECK')
        ticker = log.get('ticker', 'N/A')
        message = log.get('message', '')
        
        if action == 'SELL':
            color = '#EB0029'
            icon = '🔴'
        elif action == 'BUY':
            color = '#00873C'
            icon = '🟢'
        else:
            color = '#666'
            icon = '⚪'
        
        log_html += f"<div style='margin-bottom:8px; font-size:13px;'><span style='color:#999;'>{ts}</span> {icon} <strong style='color:{color};'>{action}</strong> {ticker}: {message}</div>"
    log_html += "</div>"
    st.markdown(log_html, unsafe_allow_html=True)
else:
    st.info("📋 Activity Log will populate when the system executes trades.")
