"""
Shared utilities for the Sniper V2 Dashboard.
Includes: Authentication, Database Connection, and Global CSS Theme.
"""
import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv
import google.generativeai as genai
import yfinance as yf

# Load environment variables
load_dotenv()

# --- 1. CONFIG & THEME ---
def load_css():
    """Injects the 'Elegant Modern 2026' CSS theme (Light Mode)."""
    st.markdown("""
    <style>
        /* GLOBAL FONT & BACKGROUND */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif; 
            color: #1D1D1F;
        }
        
        /* Main Background - Clean White/Gray */
        .stApp {
            background-color: #F8F9FA;
        }
        
        /* HEADERS */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            color: #111111 !important;
            letter-spacing: -0.5px;
        }
        
        h1 { font-size: 28px; margin-bottom: 20px; }
        h2 { font-size: 22px; margin-top: 30px; margin-bottom: 15px; }
        h3 { font-size: 18px; font-weight: 500; color: #444 !important; }
        
        /* CARDS (Minimalist White) */
        .metric-card {
            background: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        
        /* METRIC VALUES */
        .metric-label { font-size: 13px; color: #666; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
        .metric-value { font-size: 28px; font-weight: 700; color: #111; margin-top: 5px; }
        .metric-delta { font-size: 14px; font-weight: 500; margin-left: 5px; }
        .delta-pos { color: #00873C; } /* Success Green */
        .delta-neg { color: #EB0029; } /* Danger Red */
        
        /* SIDEBAR (Clean White) */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid #E5E5E5;
        }
        
        /* BUTTONS (Yahoo Finance Blue) */
        .stButton>button {
            background-color: #FFFFFF;
            color: #1D1D1F;
            border: 1px solid #D1D1D6;
            border-radius: 6px;
            font-weight: 500;
            padding: 8px 16px;
            transition: all 0.2s;
        }
        .stButton>button:hover {
            border-color: #0052FF;
            color: #0052FF;
            background-color: #F5F8FF;
        }
        .primary-btn {
            background-color: #0052FF !important;
            color: white !important;
            border: none;
        }
        
        /* DATAFRAME / TABLES */
        .stDataFrame { border: 1px solid #E0E0E0; border-radius: 8px; overflow: hidden; }
        
        /* CUSTOM TABLE STYLES */
        .sniper-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            background: white;
            border: 1px solid #E0E0E0;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .sniper-table th {
            text-align: left;
            padding: 12px 16px;
            background-color: #FAFAFA;
            color: #666;
            font-weight: 600;
            border-bottom: 2px solid #E0E0E0;
            text-transform: uppercase;
            font-size: 12px;
        }
        .sniper-table td {
            text-align: left;
            padding: 14px 16px;
            border-bottom: 1px solid #F0F0F0;
            color: #333;
        }
        .sniper-table tr:last-child td { border-bottom: none; }
        .sniper-table tr:hover { background-color: #F9F9F9; }
        
        /* BADGES */
        .badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        .badge-green { background: #E6F4EA; color: #137333; }
        .badge-red { background: #FCE8E6; color: #C5221F; }
        .badge-blue { background: #E8F0FE; color: #1967D2; }
        .badge-gray { background: #F1F3F4; color: #5F6368; }
        
        /* NAV LINKS (Sidebar) */
        .nav-link {
            display: block;
            padding: 10px 15px;
            margin: 5px 0;
            border-radius: 6px;
            color: #333;
            text-decoration: none;
            font-weight: 500;
            transition: background 0.2s;
        }
        .nav-link:hover { background: #F5F5F5; }
        .nav-link.active { background: #E8F0FE; color: #1967D2; font-weight: 600; }
        
    </style>
    """, unsafe_allow_html=True)


# --- 2. AUTHENTICATION ---
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        correct_password = st.secrets.get("DASHBOARD_PASSWORD", "Atirdror2")
        entered_password = st.session_state.get("password", "")
        
        if entered_password == correct_password:
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
                del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Access Code", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Access Code", type="password", on_change=password_entered, key="password")
        st.error("⛔ ACCESS DENIED")
        return False
    else:
        return True


# --- 3. DATABASE & API ---
@st.cache_resource
def init_clients():
    """Initializes Supabase and Gemini clients."""
    # Supabase
    supabase_url = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")
    
    supabase = None
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
    
    # Gemini
    genai_key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
    if genai_key:
        genai.configure(api_key=genai_key)
    
    return supabase


def fetch_system_status(supabase):
    """Fetches system status (SCANNING/IDLE)."""
    if not supabase: return "UNKNOWN"
    try:
        res = supabase.table('system_status').select("value").eq("key", "scan_status").execute()
        if res.data:
            return res.data[0]['value']
    except: pass
    return "IDLE"


@st.cache_data(ttl=60)
def get_live_price(ticker):
    """Fetches current live price for a single ticker."""
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
    key = os.getenv("GOOGLE_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
    if not key:
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
