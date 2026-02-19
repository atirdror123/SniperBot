"""
🎯 SNIPER TERMINAL V4 - Unified Dashboard
Merges Database (source of truth) + Alpaca (live prices) into one view.
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

# --- ENV & SECRETS SETUP ---
# Ensure secrets are available as env vars for other modules (like alpaca_client)
if hasattr(st, "secrets"):
    for key, value in st.secrets.items():
        if key not in os.environ and isinstance(value, str):
            os.environ[key] = value

load_css()

if not check_password():
    st.stop()

supabase = init_clients()
STARTING_CAPITAL = 100000

# --- ALPACA INTEGRATION ---
@st.cache_resource
def get_alpaca():
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
st.title("🎯 Sniper Terminal V4.0")
st.markdown("**Live Trading Dashboard** | Alpaca Paper Trading")

# =============================================================================
# UNIFIED DATA FETCH: DB is source of truth, Alpaca enriches with live prices
# =============================================================================
@st.cache_data(ttl=30)
def fetch_unified_data():
    """
    UNIFIED STRATEGY:
    1. Fetch ALL 'OPEN' trades from sniper_trades (DB = source of truth).
    2. Fetch Alpaca positions for live price enrichment.
    3. Merge: DB stock gets Alpaca live price if available, otherwise shows entry price.
    4. Stocks in DB but NOT in Alpaca are shown as "Pending Sync".
    """
    # --- Step 1: Database trades ---
    db_trades = {}
    if supabase:
        try:
            res = supabase.table("sniper_trades").select("*").eq("status", "OPEN").order("created_at", desc=True).execute()
            for t in (res.data or []):
                db_trades[t['ticker']] = t
        except Exception as e:
            st.error(f"DB Error: {e}")

    # --- Step 2: Alpaca positions & orders ---
    alpaca_positions = {}
    alpaca_orders = []
    account_equity = STARTING_CAPITAL
    account_cash = STARTING_CAPITAL

    if alpaca:
        try:
            account = alpaca.get_account()
            account_equity = float(account.equity)
            account_cash = float(account.cash)

            for pos in alpaca.get_positions():
                alpaca_positions[pos.symbol] = {
                    'quantity': int(pos.qty),
                    'entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price),
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc) * 100,
                }

            for o in alpaca.get_orders(status="open"):
                alpaca_orders.append({
                    'ticker': o.symbol,
                    'side': o.side.value.upper(),
                    'qty': int(o.qty) if o.qty else 0,
                    'status': o.status.value.upper(),
                    'submitted': o.submitted_at.strftime("%Y-%m-%d %H:%M")
                })
        except Exception as e:
            st.error(f"Alpaca Error: {e}")

    # --- Step 3: Merge (DB is master, Alpaca enriches) ---
    merged = []
    all_tickers = set(list(db_trades.keys()) + list(alpaca_positions.keys()))

    for ticker in sorted(all_tickers):
        db = db_trades.get(ticker)
        alp = alpaca_positions.get(ticker)

        if alp:
            # Alpaca has live data — use it
            entry = alp['entry_price']
            current = alp['current_price']
            qty = alp['quantity']
            invested = alp['cost_basis']
            value = alp['market_value']
            pnl_dollar = alp['unrealized_pl']
            pnl_pct = alp['unrealized_plpc']
            sync_status = "✅ Live"
        elif db:
            # DB only — no live price, show entry as current
            entry = db.get('entry_price', 0)
            qty = db.get('quantity', 0)
            current = entry  # No live price available
            invested = db.get('invested_amount', entry * qty)
            value = invested  # Same as invested (no live data)
            pnl_dollar = 0
            pnl_pct = 0
            sync_status = "⏳ Pending"
        else:
            continue

        # Get AI rationale from DB (if available)
        ai_notes = ""
        ai_score = 0
        if db:
            ai_notes = db.get('notes', '')
            ai_score = db.get('ai_score', 0)

        merged.append({
            'ticker': ticker,
            'qty': qty,
            'entry_price': entry,
            'current_price': current,
            'invested': invested,
            'value': value,
            'pnl_dollar': pnl_dollar,
            'pnl_pct': pnl_pct,
            'sync_status': sync_status,
            'ai_score': ai_score,
            'ai_notes': ai_notes,
        })

    # --- Step 4: Calculate aggregate metrics ---
    total_invested = sum(r['invested'] for r in merged)
    total_value = sum(r['value'] for r in merged)
    active_pnl_dollar = total_value - total_invested
    active_pnl_pct = (active_pnl_dollar / total_invested * 100) if total_invested > 0 else 0

    return {
        'positions': pd.DataFrame(merged) if merged else pd.DataFrame(),
        'orders': pd.DataFrame(alpaca_orders) if alpaca_orders else pd.DataFrame(),
        'account_equity': account_equity,
        'account_cash': account_cash,
        'total_invested': total_invested,
        'total_value': total_value,
        'active_pnl_dollar': active_pnl_dollar,
        'active_pnl_pct': active_pnl_pct,
    }

data = fetch_unified_data()
positions_df = data['positions']
orders_df = data['orders']

# =============================================================================
# HERO METRICS — Clear, Understandable, No Confusion
# =============================================================================
c1, c2, c3, c4 = st.columns(4)

total_invested = data['total_invested']
total_value = data['total_value']
active_pnl = data['active_pnl_dollar']
active_pnl_pct = data['active_pnl_pct']

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Invested</div>
        <div class="metric-value">${total_invested:,.2f}</div>
        <div class="metric-delta">Cost Basis</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    val_color = "delta-pos" if active_pnl >= 0 else "delta-neg"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Current Value</div>
        <div class="metric-value">${total_value:,.2f}</div>
        <div class="metric-delta {val_color}">${active_pnl:+,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    pnl_color = "delta-pos" if active_pnl >= 0 else "delta-neg"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Active P/L</div>
        <div class="metric-value {pnl_color}">${active_pnl:+,.2f}</div>
        <div class="metric-delta">Open Positions Only</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    pct_color = "delta-pos" if active_pnl_pct >= 0 else "delta-neg"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Active Return</div>
        <div class="metric-value {pct_color}">{active_pnl_pct:+.2f}%</div>
        <div class="metric-delta">Open Positions Only</div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# SECTION 1: ACTIVE POSITIONS TABLE
# =============================================================================
trade_count = len(positions_df) if not positions_df.empty else 0
st.markdown(f"### 📂 Active Positions ({trade_count})")

if not positions_df.empty:
    table_rows = []
    for _, row in positions_df.iterrows():
        table_rows.append({
            'Ticker': row['ticker'],
            'Status': row['sync_status'],
            'Qty': row['qty'],
            'Entry': f"${row['entry_price']:.2f}",
            'Current': f"${row['current_price']:.2f}",
            'Invested': row['invested'],
            'Value': row['value'],
            'P/L ($)': row['pnl_dollar'],
            'P/L (%)': row['pnl_pct'],
            'AI Score': row['ai_score'],
        })

    display_df = pd.DataFrame(table_rows)

    styler = display_df.style.format({
        'Invested': "${:,.2f}",
        'Value': "${:,.2f}",
        'P/L ($)': "${:+,.2f}",
        'P/L (%)': "{:+.2f}%"
    })

    def color_pnl(val):
        if isinstance(val, (int, float)):
            color = '#00873C' if val >= 0 else '#EB0029'
            return f'color: {color}; font-weight: bold'
        return ''

    try:
        styler.map(color_pnl, subset=['P/L ($)', 'P/L (%)'])
    except AttributeError:
        styler.applymap(color_pnl, subset=['P/L ($)', 'P/L (%)'])

    # Enable row selection
    event = st.dataframe(
        styler,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )

    # --- AI INSIGHTS (INTERACTIVE) ---
    if event.selection.rows:
        try:
            selected_row_index = event.selection.rows[0]
            # Get the actual data from the SOURCE dataframe (positions_df), not the display one
            # We assume display_df structure matches positions_df iteration order
            # Better: use the index to look up in positions_df
            selected_ticker = display_df.iloc[selected_row_index]['Ticker']
            
            # Find the full data for this ticker
            row_data = positions_df[positions_df['ticker'] == selected_ticker].iloc[0]
            
            st.markdown("---")
            st.markdown(f"### 🧬 Target Intel: {selected_ticker}")
            
            c1, c2 = st.columns([2, 1])
            
            with c1:
                st.markdown("#### 🧠 AI Rationale")
                if row_data.get('ai_notes'):
                    st.info(row_data['ai_notes'])
                else:
                    st.warning("No AI analysis data available for this position.")
            
            with c2:
                st.markdown("#### 🕵️ Validation")
                score = row_data.get('ai_score', 0)
                st.metric("AI Score", f"{score}/100")
                
                # Check for Closer Verdict in raw_features if available
                verdict = "N/A"
                conf = 0
                if isinstance(row_data.get('ai_rationale'), str) and "THE CLOSER" in row_data['ai_rationale']:
                     verdict = "SEE LOG" # Parsed from text if needed, or we just rely on the text above
                
                # If we had the raw dict easier, we'd show it. For now, the notes cover it.
                st.caption("Click another stock to view its intel.")
                
        except Exception as e:
            st.error(f"Error displaying details: {e}")
            
    else:
        st.info("👆 Select a stock in the table above to reveal AI Intelligence.")
else:
    st.info("🎯 No active positions found. The scanner will populate this section.")

# =============================================================================
# SECTION 1.5: PENDING ORDERS
# =============================================================================
if not orders_df.empty:
    st.markdown(f"### ⏳ Pending Orders ({len(orders_df)})")
    st.markdown("*(Orders waiting for market open)*")
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
