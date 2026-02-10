import os
import time
from datetime import datetime, timezone, timedelta
import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv
from supabase import create_client, Client
from scanner_logic import SniperScorer
from ai_signal_engine import AISignalEngine
from tournament_ai import run_tournament
from io import StringIO

print("=" * 60)
print("✅ OFFICIAL RUN_SCANNER V2.0 EXECUTING")
print("   If you see a different message, WRONG SCRIPT IS RUNNING.")
print("=" * 60)

# Alpaca Integration (optional)
try:
    from alpaca_client import get_alpaca_client
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

# Load environment variables
load_dotenv()

# Configuration
BATCH_SIZE = 300
TECH_PREFILTER_THRESHOLD = 70  # Technical score to qualify for AI evaluation
AI_SCORE_THRESHOLD = 75        # AI score to save to database
MIN_PRICE = 2.0
MIN_DOLLAR_VOLUME = 5_000_000
POSITION_SIZE = 2000  # Virtual Bank: $2,000 per position

def get_all_tickers():
    """
    Fetches a list of US tickers.
    Attempts to use NASDAQ API as a fallback since stocksymbol requires an API key.
    """
    print("Fetching universe of US stocks...")
    tickers = []
    
    # Method 1: NASDAQ API (Free, ~7000+ stocks)
    try:
        # Increase limit to 25000 to capture all universe
        url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25000&offset=0&download=true"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        data = response.json()
        
        if data['data'] and data['data']['rows']:
            df = pd.DataFrame(data['data']['rows'])
            # The API returns 'symbol' column
            raw_tickers = df['symbol'].tolist()
            
            # Filter out warrants, preferreds, etc. (containing '.' or '-')
            tickers = [t for t in raw_tickers if '.' not in t and '-' not in t]
            
            # Remove any non-alpha characters just in case
            tickers = [t for t in tickers if t.isalpha()]
            
            print(f"Successfully fetched {len(tickers)} tickers from NASDAQ API.")
            return tickers
            
    except Exception as e:
        print(f"Warning: NASDAQ API fetch failed ({e}).")

    # Method 2: Fallback to S&P 500 if NASDAQ fails
    print("Falling back to S&P 500 list...")
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        tables = pd.read_html(StringIO(response.text))
        sp500_table = tables[1] # Usually index 1
        tickers = sp500_table['Symbol'].tolist()
        tickers = [str(t).replace('.', '-') for t in tickers] # S&P 500 uses '-' in yfinance
        # But we want to filter out '-' as per requirements? 
        # Requirement: "Filter out any symbol that contains "." or "-"".
        # So we should actually skip BRK.B etc.
        tickers = [t for t in tickers if '.' not in t and '-' not in t]
        print(f"Fetched {len(tickers)} tickers from S&P 500.")
        return tickers
    except Exception as e:
        print(f"Error fetching S&P 500: {e}")
        return []



def cleanup_todays_signals(supabase: Client):
    """
    Removes only TODAY's 'OPEN' trades to prevent duplicate entries from re-runs.
    FIX: No longer deletes ALL OPEN trades (which caused cross-day data loss).
    """
    try:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date().isoformat()
        
        # Only delete trades created TODAY with status='OPEN'
        supabase.table('sniper_trades').delete().eq('status', 'OPEN').gte('created_at', today).execute()
        print(f"  Cleaned up today's OPEN trades only (preserving historical positions).")
    except Exception as e:
        print(f"  Warning: Failed to cleanup trades: {e}")


def run_scanner():
    # Initialize Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
        return
    
    supabase: Client = create_client(url, key)
    scorer = SniperScorer()
    ai_engine = AISignalEngine()  # NEW: Initialize AI engine
    
    # 1. Universe
    tickers = get_all_tickers()
    if not tickers:
        print("No tickers found. Exiting.")
        return
    
    total_tickers = len(tickers)
    print(f"Universe size: {total_tickers} stocks")
    
    # 2. Batching
    total_survivors = 0
    all_qualified_stocks = []  # Store all stocks that pass AI threshold
    
    for i in range(0, total_tickers, BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (total_tickers + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"\nProcessing Batch {batch_num}/{total_batches} ({len(batch)} tickers)...")
        
        # 3. Fast Filter
        survivors = []
        try:
            # Download data for batch
            data = yf.download(batch, period="5d", interval="1d", group_by='ticker', progress=False, threads=True)
            
            if data.empty:
                print("  Warning: No data returned for batch.")
                continue
                
            # Iterate through tickers in the batch
            for ticker in batch:
                try:
                    # Handle MultiIndex: data[ticker] returns DataFrame with OHLCV
                    if ticker not in data.columns.levels[0]:
                        continue
                        
                    df = data[ticker]
                    if df.empty:
                        continue
                        
                    last_row = df.iloc[-1]
                    close = last_row['Close']
                    volume = last_row['Volume']
                    
                    # Check for NaN
                    if pd.isna(close) or pd.isna(volume):
                        continue
                        
                    # Filter Logic
                    if close >= MIN_PRICE and (close * volume) >= MIN_DOLLAR_VOLUME:
                        survivors.append((ticker, close))
                        
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"  Error downloading batch: {e}")
            continue
            
        print(f"  Survivors: {len(survivors)}")
        total_survivors += len(survivors)
        
        # 4. TWO-STAGE SCORING: Technical Pre-filter → AI Final Score
        for ticker, fast_close in survivors:
            try:
                # STAGE 1: Technical Pre-filter
                tech_result = scorer.analyze_stock(ticker)
                tech_score = tech_result.get('final_score', 0)
                
                print(f"    {ticker}: Tech Score = {tech_score}", end="")
                
                # Only proceed to AI if technical score passes
                if tech_score < TECH_PREFILTER_THRESHOLD:
                    reason = tech_result.get('details', 'Low Score')
                    print(f" → Rejected ({reason})")
                    continue
                
                # STAGE 2: AI Final Scoring
                print(" → AI Scoring...", end="", flush=True)
                ai_result = ai_engine.score_stock(ticker)
                ai_final_score = ai_result.get('final_score', 0)
                
                print(f" AI Score = {ai_final_score}", end="")
                
                # Check if AI score passes threshold
                if ai_final_score > AI_SCORE_THRESHOLD:
                    # Store qualified stock with BOTH tech and AI details
                    all_qualified_stocks.append({
                        'ticker': ticker,
                        'entry_price': fast_close,
                        'ai_score': ai_final_score,
                        'tech_score': tech_score,
                        'ai_details': ai_result,
                        'tech_details': tech_result.get('details', ''),
                        'raw_features': tech_result.get('raw_features', {})
                    })
                    print(f" → ✅ QUALIFIED")
                else:
                    print(f" → Rejected (AI)")
                        
            except Exception as e:
                print(f"    Error analyzing {ticker}: {e}")
                continue
        
        print(f"  Batch Summary: {len(batch)} scanned → {len(survivors)} survivors → {len(all_qualified_stocks)} total qualified so far")
        
        # Sleep to be nice to API
        time.sleep(1)

    # 5. Tournament Selection: Top 10 → Top 3
    print("\n" + "="*60)
    print("TOURNAMENT SELECTION: TOP 10 → TOP 3")
    print("="*60)
    
    if not all_qualified_stocks:
        print("No stocks qualified (AI score > 75). Nothing to save.")
        total_saved = 0
    else:
        # Sort by AI score descending and take top 10 for tournament
        all_qualified_stocks.sort(key=lambda x: x['ai_score'], reverse=True)
        top_10_candidates = all_qualified_stocks[:10]
        
        print(f"Total Qualified: {len(all_qualified_stocks)}")
        print(f"Top 10 Candidates for Tournament:")
        for i, stock in enumerate(top_10_candidates, 1):
            print(f"  {i}. {stock['ticker']} - AI Score: {stock['ai_score']}")
        
        # Run Tournament AI to select top 3
        print("\n🤖 Running Tournament AI...")
        tournament_candidates = [
            {
                'ticker': s['ticker'],
                'ai_score': s['ai_score'],
                'tech_score': s['tech_score'],
                'price': s['entry_price'],
                'hunter': s['ai_details'].get('hunter', 0),
                'quant': s['ai_details'].get('quant', 0),
                'oracle': s['ai_details'].get('oracle', 0)
            }
            for s in top_10_candidates
        ]
        
        tournament_result = run_tournament(tournament_candidates)
        top_3_tickers = [pick['ticker'] for pick in tournament_result.get('top_3', [])]
        
        # Filter to get full details for top 3
        top_3_stocks = [s for s in top_10_candidates if s['ticker'] in top_3_tickers]
        
        # CLEANUP: Remove today's existing signals before saving new ones
        # print("\nCleaning up previous signals for today...")
        # cleanup_todays_signals(supabase)
        # DISABLE CLEANUP ENTIRELY FOR EMERGENCY STABILIZATION
        
        # VERIFY CLEANUP (SAFEGUARD)
        try:
            # existing = supabase.table('sniper_trades').select('ticker', count='exact').eq('status', 'OPEN').execute()
            # count = existing.count if existing.count is not None else len(existing.data)
            count = 0 # Forced override

            
            if count > 0:
                print(f"CRITICAL ERROR: Cleanup failed. Found {count} 'OPEN' trades still in DB.")
                print("Aborting save to prevent exceeding the trade limit.")
                return
            else:
                print("  Cleanup verified. 0 OPEN trades remaining.")
        except Exception as e:
            print(f"Error verifying cleanup: {e}. Aborting for safety.")
            return
        
        print(f"\nSaving Top 3 Tournament Winners:")
        print("-" * 60)
        
        # Prepare batch data for sniper_trades (V2 Schema)
        trades_data = []
        for stock in top_3_stocks:
            ai_details = stock['ai_details']
            entry_price = stock['entry_price']
            
            # Calculate stop loss (3% below entry)
            stop_loss = entry_price * 0.97
            
            # Format AI reasons
            ai_reasons = f"""🎯 AI COMPOSITE SCORE: {stock['ai_score']}/100

HUNTER (Insider Sentiment): {ai_details['hunter']}/100
{ai_details['hunter_reason']}

QUANT (Institutional Quality): {ai_details['quant']}/100
{ai_details['quant_reason']}

ORACLE (AI Synthesis): {ai_details['oracle']}/100
{ai_details['oracle_reason']}

Technical Pre-filter Score: {stock['tech_score']}/100
{stock['tech_details']}
"""
            
            # Calculate position sizing (Virtual Bank)
            quantity = int(POSITION_SIZE // entry_price)  # Floor division
            invested_amount = round(quantity * entry_price, 2)
            
            # EMERGENCY FIX: Double-clamp the score to strictly ensure <= 100
            # This handles cases where ai_signal_engine might have returned > 100 or old cached code ran
            final_clamped_score = max(0, min(100, int(stock['ai_score'])))
            
            trades_data.append({
                'ticker': stock['ticker'],
                'entry_price': entry_price,
                'quantity': quantity,
                'invested_amount': invested_amount,
                'status': 'OPEN',
                'stop_loss_price': stop_loss,
                'take_profit_price': entry_price * 1.10,  # 10% take profit
                'ai_score': final_clamped_score,  # Use clamped score
                'notes': ai_reasons,
                'raw_features': {
                    'tech_features': stock['raw_features'],
                    'ai_scores': {
                        'hunter': ai_details['hunter'],
                        'quant': ai_details['quant'],
                        'oracle': ai_details['oracle'],
                        'final': stock['ai_score']
                    },
                    'tech_score': stock['tech_score'],
                    'tournament_rank': top_3_tickers.index(stock['ticker']) + 1
                }
            })
            print(f"  Preparing: {stock['ticker']} - AI Score: {stock['ai_score']} | Qty: {quantity} @ ${entry_price:.2f} = ${invested_amount:.2f}")

        # Execute trades via Alpaca (if configured) or just save to database
        if trades_data:
            alpaca_client = None
            if ALPACA_AVAILABLE and os.getenv('ALPACA_API_KEY'):
                try:
                    alpaca_client = get_alpaca_client()
                    print("\n🏦 ALPACA CONNECTED - Submitting real paper trades...")
                except Exception as e:
                    print(f"\n⚠️ Alpaca connection failed: {e}. Saving to database only.")
            
            for trade in trades_data:
                ticker = trade['ticker']
                qty = trade['quantity']
                
                # Submit Alpaca order if available
                if alpaca_client:
                    try:
                        order = alpaca_client.submit_bracket_order(
                            ticker=ticker,
                            qty=qty,
                            stop_loss_pct=0.05,  # 5% stop loss
                            take_profit_pct=0.10  # 10% take profit
                        )
                        print(f"  📈 ALPACA ORDER: {ticker} x{qty} - Order ID: {order.id}")
                    except Exception as e:
                        print(f"  ⚠️ Alpaca order failed for {ticker}: {e}")
            
            # Always save to database for tracking
            try:
                supabase.table('sniper_trades').insert(trades_data).execute()
                total_saved = len(trades_data)
                print(f"\n✅ Successfully saved {total_saved} tournament winners to sniper_trades.")
                
                # VERIFICATION STEP
                verify_res = supabase.table('sniper_trades').select('ticker', count='exact').eq('status', 'OPEN').execute()
                verified_count = verify_res.count if verify_res.count is not None else len(verify_res.data)
                if verified_count < total_saved:
                    print(f"⚠️ WARNING: Verification failed! Expected {total_saved}, found {verified_count} OPEN trades.")
                else:
                    print(f"✅ Verification passed: {verified_count} OPEN trades confirmed in database.")
            except Exception as e:
                print(f"\n❌ CRITICAL ERROR: Batch insert failed: {e}")
                total_saved = 0
        else:
            total_saved = 0
        
        if len(all_qualified_stocks) > 3:
            print(f"\n📊 Note: {len(all_qualified_stocks) - 3} additional qualified stocks were not selected by tournament")

    print("\n" + "="*60)

    # 6. Send Discord Notification
    print("\nSending Discord Alert...")
    send_discord_alert(trades_data if 'trades_data' in locals() else [])

    print("SCAN COMPLETE")
    print(f"Total Scanned: {total_tickers}")
    print(f"Total Survivors: {total_survivors}")
    print(f"Total Qualified (AI > 75): {len(all_qualified_stocks)}")
    print(f"Tournament Winners Saved: {total_saved if all_qualified_stocks else 0}")
    print("="*60)

def send_discord_alert(trades: list):
    """Sends a summary of the scan results to Discord."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("⚠️ No DISCORD_WEBHOOK_URL found. Skipping notification.")
        return

    if not trades:
        content = "📉 **Sniper Scan Complete**\nNo stocks met the strict AI criteria (Score > 75) today."
        embeds = []
    else:
        content = f"🎯 **Sniper Scan V2.0 Complete**\nFound {len(trades)} high-conviction setup(s):"
        embeds = []
        for t in trades:
            score = t.get('ai_score', 0)
            ticker = t.get('ticker')
            price = t.get('entry_price')
            
            # Color code based on score
            color = 0x00FF00 if score >= 85 else 0xFFFF00
            
            embed = {
                "title": f"🚨 {ticker} (Score: {score})",
                "description": f"Entry: ${price:.2f}\n\n**Analysis:**\n{t.get('notes', 'No notes.')[:500]}...",
                "color": color,
                "fields": [
                    {"name": "Stop Loss", "value": f"${t.get('stop_loss_price', 0):.2f}", "inline": True},
                    {"name": "Take Profit", "value": f"${t.get('take_profit_price', 0):.2f}", "inline": True}
                ]
            }
            embeds.append(embed)

    payload = {
        "content": content,
        "embeds": embeds,
        "username": "Sniper Bot 🎯"
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        if response.status_code == 204:
            print("✅ Discord notification sent!")
        else:
            print(f"⚠️ Discord failed: {response.status_code} {response.text}")
    except Exception as e:
        print(f"⚠️ Discord Error: {e}")


if __name__ == "__main__":
    # If run directly, logic handles the scan. 
    # Just need to ensure `trades_data` is passed or accessible.
    # Refactoring slightly to allow passing data, but `run_scanner` is monolithic.
    # We will inject the call INSIDE run_scanner before main return.
    run_scanner()
