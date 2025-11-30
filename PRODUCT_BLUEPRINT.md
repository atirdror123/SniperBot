# 🚀 PRODUCT BLUEPRINT: The "Sniper" Algo-Bot (Full Stack)

## 1. System Vision
We are building a self-hosted, closed-loop algorithmic trading system.
**Core Philosophy:** "Sniper Mode" - The system is NOT forced to trade daily. It only signals when multiple data sources (Technical + Fundamental + Social) align with high probability (>85% Confidence Score).
**End Goal:** A dashboard showing live opportunities and a "Paper Trading" simulation tracking a virtual $100k portfolio.

---

## 2. Architecture (Single Stack)
We will use a pure Python stack to allow the Anti-Gravity Agent to manage the entire lifecycle easily.
*   **Backend:** Python 3.11+
*   **Database:** Supabase (PostgreSQL) - For storing historic data, trades, and simulation state.
*   **Frontend:** **Streamlit** (Python-based UI). This allows us to build the dashboard directly from the Python logic without needing a separate React app.
*   **Hosting:** Local / Cloud Run (handled by Anti-Gravity environment).

## 3. Data Sources (The Aggregation Layer)
The bot must aggregate data to confirm signals (cross-validation):
1.  **Primary:** Financial Modeling Prep (FMP) API -> Price, Technicals, Sentiment, Insider.
2.  **Secondary (Verification):** `yfinance` -> Verify price action and volume anomalies.
3.  **News Logic:** Fetch news via FMP/NewsAPI and use LLM to score them (-1 to +1).

---

## 4. The Logic: "Sniper" Scoring Engine
The system calculates a `ConfidenceScore` (0-100).
*   **Hard Filters:** Price > $2, Market Cap > $100M, Dollar Volume > $5M.
*   **The "Green Light" Threshold:** Only stocks with Score > **85** appear in the "Active Signal" table.
*   **Scoring Factors:**
    *   *Technical:* Trend Alignment + Breakout Proximity.
    *   *Social:* Spike in social volume + Positive sentiment (AI analyzed).
    *   *Insider:* Recent cluster buying.

---

## 5. UI/UX: The Dashboard (Streamlit)
The interface will have two main tabs:

### Tab A: The Scanner (The Sniper Scope)
*   **Live Table:** Shows only the stocks that passed the threshold today.
*   **Columns:** Ticker, Price, Confidence Score, "Reason for Entry" (AI generated text).
*   **Visuals:** Green/Red indicators based on real-time price change since signal.

### Tab B: Paper Trading Simulation (Future Phase)
*   **Virtual Balance:** Starts at $100,000.
*   **Position Sizing:**
    *   Score 85-90: Allocate 2% of portfolio.
    *   Score 90-95: Allocate 5% of portfolio.
    *   Score 95+: Allocate 8% of portfolio.
*   **Metrics:** Total P&L, Win Rate %, Equity Curve Graph.

---

## 6. Execution Roadmap for Agents
1.  **Setup:** Initialize Python env, install `streamlit`, `supabase`, `requests`, `pandas`.
2.  **Keys:** Securely load API keys from `.env` file.
3.  **Backend:** Build the `DataAggregator` class (fetches from FMP + yfinance).
4.  **Logic:** Build the `SniperScorer` class (implements the math).
5.  **Database:** Create Supabase tables (`signals`, `portfolio_sim`).
6.  **Frontend:** Build `app.py` using Streamlit to visualize the DB data.