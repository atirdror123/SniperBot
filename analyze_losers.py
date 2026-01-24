"""
Analyze Losing Stocks from Legacy Database
Purpose: Extract patterns from losers to improve AI learning
Uses live prices from yfinance to calculate returns
"""
from dotenv import load_dotenv
import os
import yfinance as yf
import sys

load_dotenv()
from supabase import create_client

# Write output to both console and file
class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

output_file = open('analysis_output.txt', 'w', encoding='utf-8')
sys.stdout = Tee(sys.__stdout__, output_file)

sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Get legacy stocks
result = sb.table('sniper_signals').select('*').eq('portfolio', 'LEGACY').execute()
stocks = result.data

if not stocks:
    print("No legacy stocks found")
    exit()

print(f"Total Legacy: {len(stocks)}")

# Get all unique tickers for batch price fetch
tickers = list(set([s['ticker'] for s in stocks if s.get('ticker')]))
print(f"Fetching live prices for {len(tickers)} unique tickers...")

# Fetch batch prices
try:
    price_data = yf.download(tickers, period="1d", progress=False)['Close']
    if len(tickers) == 1:
        prices = {tickers[0]: float(price_data.iloc[-1]) if not price_data.empty else None}
    else:
        prices = {t: float(price_data[t].iloc[-1]) if t in price_data.columns and not price_data[t].isna().all() else None for t in tickers}
except Exception as e:
    print(f"Price fetch error: {e}")
    prices = {}

print(f"Got prices for {len([p for p in prices.values() if p])} tickers")

# Calculate returns
valid_stocks = []
for s in stocks:
    ticker = s.get('ticker')
    entry = s.get('entry_price', 0) or 0
    current = prices.get(ticker)
    
    if entry > 0 and current and current > 0:
        s['calc_return'] = ((current - entry) / entry) * 100
        s['current_price'] = current
        valid_stocks.append(s)

print(f"Stocks with valid return data: {len(valid_stocks)}")

if not valid_stocks:
    print("No stocks have valid price data for return calculation!")
    exit()

# Separate winners and losers
winners = [s for s in valid_stocks if s['calc_return'] >= 0]
losers = [s for s in valid_stocks if s['calc_return'] < 0]

print(f"Winners: {len(winners)}, Losers: {len(losers)}")
if len(winners) + len(losers) > 0:
    print(f"Win Rate: {len(winners)/(len(winners)+len(losers))*100:.1f}%")

if not losers:
    print("\nNo losers found! All stocks are in profit 🎉")
    exit()

# Analyze top 15 losers
top_losers = sorted(losers, key=lambda x: x['calc_return'])[:15]

print("\n" + "="*80)
print("TOP 15 LOSERS (Worst Performers)")
print("="*80)
print(f"{'Ticker':<8} | {'Return':>8} | {'Entry':>8} | {'Now':>8} | {'H':>4} | {'C':>4} | {'Q':>4} | {'O':>4}")
print("-"*80)

loser_lens_totals = {'HUNTER': [], 'CHARTIST': [], 'QUANT': [], 'ORACLE': []}

def get_lens(stock):
    """Extract lens scores from either lens_scores column or raw_features.lens_scores"""
    lens = stock.get('lens_scores', {}) or {}
    if not lens or all(v == 0 for v in lens.values()):
        raw = stock.get('raw_features', {}) or {}
        lens = raw.get('lens_scores', {}) or {}
    return lens

for l in top_losers:
    lens = get_lens(l)
    h = lens.get('HUNTER', 0) or 0
    c = lens.get('CHARTIST', 0) or 0
    q = lens.get('QUANT', 0) or 0
    o = lens.get('ORACLE', 0) or 0
    
    loser_lens_totals['HUNTER'].append(h)
    loser_lens_totals['CHARTIST'].append(c)
    loser_lens_totals['QUANT'].append(q)
    loser_lens_totals['ORACLE'].append(o)
    
    print(f"{l['ticker']:<8} | {l['calc_return']:>+7.1f}% | ${l.get('entry_price', 0):>7.2f} | ${l.get('current_price', 0):>7.2f} | {h:>4.0f} | {c:>4.0f} | {q:>4.0f} | {o:>4.0f}")

# Calculate averages for top losers
print("\n" + "="*80)
print("LOSER PATTERN ANALYSIS (Top 15 Losers vs All Winners)")
print("="*80)

avg_loser = {
    'HUNTER': sum(loser_lens_totals['HUNTER'])/len(loser_lens_totals['HUNTER']) if loser_lens_totals['HUNTER'] else 0,
    'CHARTIST': sum(loser_lens_totals['CHARTIST'])/len(loser_lens_totals['CHARTIST']) if loser_lens_totals['CHARTIST'] else 0,
    'QUANT': sum(loser_lens_totals['QUANT'])/len(loser_lens_totals['QUANT']) if loser_lens_totals['QUANT'] else 0,
    'ORACLE': sum(loser_lens_totals['ORACLE'])/len(loser_lens_totals['ORACLE']) if loser_lens_totals['ORACLE'] else 0,
}

# Compare with winners
winner_lens_totals = {'HUNTER': [], 'CHARTIST': [], 'QUANT': [], 'ORACLE': []}
for w in winners:
    lens = get_lens(w)
    winner_lens_totals['HUNTER'].append(lens.get('HUNTER', 0) or 0)
    winner_lens_totals['CHARTIST'].append(lens.get('CHARTIST', 0) or 0)
    winner_lens_totals['QUANT'].append(lens.get('QUANT', 0) or 0)
    winner_lens_totals['ORACLE'].append(lens.get('ORACLE', 0) or 0)

avg_winner = {
    'HUNTER': sum(winner_lens_totals['HUNTER'])/len(winner_lens_totals['HUNTER']) if winner_lens_totals['HUNTER'] else 0,
    'CHARTIST': sum(winner_lens_totals['CHARTIST'])/len(winner_lens_totals['CHARTIST']) if winner_lens_totals['CHARTIST'] else 0,
    'QUANT': sum(winner_lens_totals['QUANT'])/len(winner_lens_totals['QUANT']) if winner_lens_totals['QUANT'] else 0,
    'ORACLE': sum(winner_lens_totals['ORACLE'])/len(winner_lens_totals['ORACLE']) if winner_lens_totals['ORACLE'] else 0,
}

print(f"\n{'Lens':<10} | {'Loser Avg':>10} | {'Winner Avg':>10} | {'Diff':>8} | {'Insight':<30}")
print("-"*80)

significant_findings = []
for lens in ['HUNTER', 'CHARTIST', 'QUANT', 'ORACLE']:
    diff = avg_winner[lens] - avg_loser[lens]
    insight = ""
    if diff > 5:
        insight = f"⚠️ Winners +{diff:.0f} pts higher"
        significant_findings.append((lens, diff, 'winners higher'))
    elif diff < -5:
        insight = f"🔴 Losers +{abs(diff):.0f} pts higher (CONCERN)"
        significant_findings.append((lens, diff, 'losers higher'))
    else:
        insight = "Similar (no strong signal)"
    print(f"{lens:<10} | {avg_loser[lens]:>10.1f} | {avg_winner[lens]:>10.1f} | {diff:>+7.1f} | {insight}")

# Summary
print("\n" + "="*80)
print("📊 KEY FINDINGS")
print("="*80)

if significant_findings:
    for lens, diff, direction in significant_findings:
        if direction == 'losers higher':
            print(f"  🚨 {lens}: Losers scored {abs(diff):.0f} points HIGHER than winners")
            print(f"     → Consider REDUCING {lens} weight or adding penalty")
        else:
            print(f"  ✅ {lens}: Winners scored {diff:.0f} points higher (expected)")
else:
    print("  No significant differences found between winner and loser lens profiles.")

print("\n" + "="*80)
print("RECOMMENDED WEIGHT ADJUSTMENTS")
print("="*80)

# Calculate adjustment factors based on difference
adjustments = {}
for lens in ['HUNTER', 'CHARTIST', 'QUANT', 'ORACLE']:
    diff = avg_winner[lens] - avg_loser[lens]
    if diff > 10:
        adjustments[lens] = 0.1  # Boost this lens weight
    elif diff > 5:
        adjustments[lens] = 0.05
    elif diff < -10:
        adjustments[lens] = -0.1  # Reduce this lens weight
    elif diff < -5:
        adjustments[lens] = -0.05
    else:
        adjustments[lens] = 0

    if adjustments[lens] != 0:
        print(f"  {lens}: {adjustments[lens]:+.2f} adjustment suggested")
    else:
        print(f"  {lens}: No adjustment needed")
