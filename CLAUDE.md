# CLAUDE.md - AI Assistant Guide for SniperBot

## Project Overview

**SniperBot (Sentient Sniper)** is an automated stock scanning and paper-trading system. It scans ~8,000 US equities daily, scores them through a 4-lens system, and manages paper trades via Alpaca. The system runs autonomously via GitHub Actions with a Supabase backend.

The canonical design document is `PRODUCT_BLUEPRINT.md` — treat it as the single source of truth for business logic decisions.

## Tech Stack

- **Language**: Python 3.12
- **Database**: Supabase (PostgreSQL)
- **Market Data**: Yahoo Finance (yfinance), Financial Modeling Prep (FMP)
- **AI**: Google Gemini API (generativeai)
- **Paper Trading**: Alpaca API (alpaca-py)
- **Dashboard**: Streamlit + Plotly + st-aggrid
- **Deployment**: Docker (Gunicorn on port 8080), GitHub Actions
- **Notifications**: Discord webhooks

## Architecture — The 5 Layers

```
1. Iron Dome (iron_dome.py)         → Market safety check (SPY/VIX thresholds)
2. Data Ingestion (data_ingestion.py) → Hybrid multi-source data fetching
3. Signal Engine (signal_engine.py)   → 4-lens scoring with dynamic averaging
4. Reinforcement Brain (reinforcement_learner.py) → Self-learning weight adjustment
5. Portfolio Manager (portfolio_manager.py) → Risk checks, diversification, position sizing
```

Orchestrated by `main_sentient.py`. The daily scanner entry point is `run_scanner.py`.

## Key Entry Points

| File | Purpose | How it runs |
|---|---|---|
| `run_scanner.py` | Daily stock scan (~8,000 tickers) | GitHub Actions daily at 14:45 UTC |
| `nightly_review.py` | Self-learning review of past picks | GitHub Actions daily at 22:00 UTC |
| `position_manager.py` | Automated trade exit management | GitHub Actions hourly during market hours |
| `main_sentient.py` | Full orchestrator with safety checks | Manual / can use `--test` flag (50 stocks) |
| `main.py` | Flask web service (`/scan` endpoint) | Docker / Gunicorn |
| `dashboard.py` | Streamlit dashboard | Codespaces / local (`streamlit run dashboard.py`) |

## Directory Structure

```
SniperBot/
├── .github/workflows/     # 3 GitHub Actions workflows (scan, review, monitor)
├── .devcontainer/         # Codespaces config (Python 3.11, Streamlit on 8501)
├── pages/                 # Streamlit sub-pages
│   ├── 1_Legacy_Database.py
│   └── 2_The_Brain.py
├── migrations/            # Database migration scripts
├── # Core system (~15 key files)
├── iron_dome.py           # Layer 1: Market safety
├── data_ingestion.py      # Layer 2: Data fetching with fallbacks
├── signal_engine.py       # Layer 3: Scoring engine
├── scanner_logic.py       # Technical/fundamental scoring helpers
├── reinforcement_learner.py # Layer 4: Self-learning
├── portfolio_manager.py   # Layer 5: Risk/position management
├── ai_signal_engine.py    # Gemini AI scoring integration
├── alpaca_client.py       # Paper trading wrapper
├── filter_config.py       # All tunable parameters (thresholds, weights, exits)
├── # Supporting services
├── discord_service.py     # Webhook notifications
├── network_utils.py       # HTTP retry/session management
├── scan_logger.py         # Structured logging
├── # Many backtest_*.py, check_*.py, audit_*.py utility scripts
├── PRODUCT_BLUEPRINT.md   # System Bible — source of truth
├── Dockerfile             # Python 3.12-slim, Gunicorn
└── requirements.txt       # Python dependencies
```

## Scoring System

4 lenses, dynamically averaged (missing data is ignored, not penalized):

- **Quant**: Dark pool / institutional money signals
- **Oracle**: Fundamentals (ROE, PEG) + news sentiment
- **Hunter**: Insider activity (cluster buys) — highest-weighted lens (1.5x)
- **Chartist**: Technical indicators (RSI, volatility, SMA/EMA alignment)

**Thresholds**: Score > 75 = candidate. Top 10 saved to DB per scan.

## Hard Rules (Do Not Change Without Discussion)

- **Rate limiting**: 1.0s sleep per stock during deep scan. Never below 0.8s.
- **Gemini budget**: 500 requests/day cap.
- **Hard filters**: Price > $2, Dollar Volume > $5M, Price > SMA150/200.
- **Exit rules**: -3% stop loss, +10% take profit, time-stop at 72h with < 1% move.
- **Max positions**: 10 stocks, max correlation 0.7 between holdings.
- **Paper trading position size**: $2,000 per trade, $100,000 virtual capital.

## Environment Variables

Required secrets (set in GitHub Actions and locally via `.env`):

| Variable | Required | Notes |
|---|---|---|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_KEY` | Yes | Note: GitHub secret may be `SUPABASEKEY` (no underscore) — workflows handle both |
| `FMP_API_KEY` | Yes | Financial Modeling Prep API |
| `GOOGLE_API_KEY` | Yes | Gemini AI API |
| `ALPACA_API_KEY` | No | Paper trading |
| `ALPACA_SECRET_KEY` | No | Paper trading |
| `DISCORD_WEBHOOK_URL` | No | Notifications |

## Database Tables (Supabase)

- `sniper_signals` — Daily scan results (scored candidates)
- `sniper_trades` — Active paper trading positions
- `sentient_memory` — Historical outcomes for self-learning
- `lens_weights` — Dynamic lens weights per market regime
- `scan_summaries` — Execution logs per scan
- `paper_portfolio` — Virtual holdings
- `ai_job_queue` — Async Gemini scoring queue
- `bot_config` — Global strategy configuration
- `system_status` — Operational status beacon

## Development Workflow

### Local Testing

```bash
# Quick test (50 stocks only)
python main_sentient.py --test

# Run dashboard locally
streamlit run dashboard.py

# Run full scanner
python run_scanner.py
```

### Dependencies

```bash
pip install -r requirements.txt
```

### Docker

```bash
docker build -t sniperbot .
docker run -p 8080:8080 --env-file .env sniperbot
```

## Coding Conventions

- **Defensive programming**: Every external data source must have fallback logic. Never let a missing API response crash the scan.
- **Rate limit awareness**: All loops over stocks must include appropriate sleep intervals. Check `PRODUCT_BLUEPRINT.md` for current limits.
- **Score clamping**: All lens scores must be clamped to 0-100 range.
- **Logging**: Use structured logging with timestamps and module names. The scanner prints `[ALIVE]` heartbeats every 5 stocks.
- **No hardcoded thresholds**: Use `filter_config.py` for all tunable parameters.
- **Data resilience**: Use `network_utils.py` retry sessions for HTTP calls. Handle `None` returns gracefully throughout the pipeline.

## Common Pitfalls

- The `SUPABASE_KEY` GitHub secret historically had no underscore (`SUPABASEKEY`). Workflows use `${{ secrets.SUPABASE_KEY || secrets.SUPABASEKEY }}` to handle both.
- Many `backtest_*.py` and `check_*.py` files are one-off utilities from iterative development — not part of the core system.
- The Dockerfile runs Gunicorn with a 60-minute timeout because full scans of ~8,000 stocks take significant time.
- yfinance can be flaky — always wrap calls with error handling and fallback logic.
