# 📜 SENTIENT SNIPER: SYSTEM BIBLE & LOGIC REFERENCE

> [!IMPORTANT]
> **This document is the SINGLE SOURCE OF TRUTH.**
> Any code changes must align with the logic defined here. If logic changes, update this document first.

---

## 1. Core Architecture (The 5 Layers)

The system operates as a **Monolithic Python Application** (`main_sentient.py`) orchestrating 5 distinct layers:

1.  **Iron Dome (`iron_dome.py`)**: Global Safety & Liquidity verification.
2.  **Data Ingestion (`data_ingestion.py`)**: Hybrid fetching engine (FMP + YFinance).
3.  **Signal Engine (`signal_engine.py`)**: 4-Dimensional Scoring & Dynamic Averaging.
4.  **Reinforcement Brain (`reinforcement_learner.py`)**: Adaptive weighting (currently static 1.0 until live feedback loop active).
5.  **Portfolio Manager (`portfolio_manager.py`)**: Risk checks & Diversification (Top 10 max).

---

## 2. The Hybrid Data Engine (Tiered Sourcing)

To prevent "Missing Data" from breaking the scan, every data point has a redundant fallback.

| Metric | Primary Source (Tier A) | Secondary Source (Tier B) | Logic |
| :--- | :--- | :--- | :--- |
| **Market Universe** | FMP Screener / NASDAQ | FMP (Limit 10k) | Fetches raw list of tickers. |
| **Price/Volume** | Yahoo Finance (Batch) | N/A | Used for fast technical filtering. |
| **Technicals (SMA150)** | Yahoo Finance | N/A | Trend Verification. |
| **Insiders** | FMP Insider Transaction | **YFinance Insider** | Scans for "Buy" keywords in last 90 days. |
| **Institutions** | FMP Holders | **YFinance Holders** | Checks for >10M shares held by top funds. |
| **Fundamentals** | FMP Ratios (ROE/PEG) | **YFinance Info** | Validates Financial Health. |
| **News Sentiment** | Yahoo Finance News | FMP Social | NLP Analysis of titles. |

> [!NOTE]
> If a Data Point is **Totally Unavailable** (both tiers fail), the engine returns `None`.

---

## 3. The Filtration Pipeline (Funnel)

The scan processes stocks in a strict Funnel to optimize speed and API usage.

1.  **Universe Fetch**: ~8,000 Stocks.
2.  **Batch Filter (Fast)**:
    *   **Price Check**: Must be > $2.00.
    *   **Liquidity Check**: (Price * AvgVolume) > $5,000,000.
    *   **Trend Check**: Price > SMA150 (Long Term Trend).
    *   *Result*: Reduces list to ~1,500 candidates.
3.  **Deep Scan (Slow)**:
    *   Iterates survivors with **1.0s Sleep** (Rate Limit Safety).
    *   Fetches deep data (Insiders, Fundamentals).
    *   Result: ~1,500 Scored Setups.

---

## 4. The Scoring Logic (Dynamic Averaging)

The system does **NOT** penalize stocks for missing data. It uses **Dynamic Averaging**.

### The Lenses
1.  **Quant**: Dark Pool / Institutional Money.
2.  **Oracle**: Fundamental Quality (ROE, PEG) + Sentiment.
3.  **Hunter**: Insider Activity (Cluster Buys).
4.  **Chartist**: Technicals (RSI, Volatility).

### The Formula
$$ \text{Final Score} = \frac{\sum(\text{Active Lens Scores})}{\text{Count of Active Lenses}} $$

**Example**:
*   Chart: 80
*   Oracle: 80
*   Hunter: *Missing/No Data* (Ignored)
*   **Final Score**: (80 + 80) / 2 = **80**. (Passes).
*   *Legacy (Bad) Score*: (80 + 80 + 0) / 3 = 53. (Fails).

### Thresholds
*   **Candidate**: Final Score > **75**.
*   **Selection**: Top 10 Highest Scores are saved to DB.

---

## 5. Operational Rules

1.  **Rate Limits**:
    *   **Deep Scan Sleep**: **1.0 Seconds** per stock.
    *   *Reason*: Hybrid Engine makes ~3 API calls per stock. 3 * 60 = 180 calls/min. (Limit is 300).
    *   *Constraint*: Do NOT lower this below 0.8s.

2.  **Cloud Automation**:
    *   Platform: GitHub Actions.
    *   Schedule: Daily at 13:45 UTC.
    *   **Secrets Required**: `FMP_API_KEY`, `GOOGLE_API_KEY`, `SUPABASE_KEY` (No underscore!), `SUPABASE_URL`.
    *   *Note*: Cloud logs are NOT visible locally. Check DB for results.

3.  **Local "Turbo" Test**:
    *   Command: `python main_sentient.py --test`
    *   Scope: 50 Stocks.
    *   Use this to verify system health before full scans.

---

## 6. Feedback & Output

*   **Heartbeat**: Console prints `[ALIVE] Scanned X/Y...` every 5 stocks during Deep Scan.
*   **Dashboard**: Streamlit (`dashboard.py`) visualizes `sniper_signals` table.
*   **Memory**: Execution saves snapshot to `sentient_memory` for future AI training.