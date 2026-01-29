"""
Deep Investigation: Why are lens scores identical?
Let's examine the raw_features data to understand what's happening
"""
from dotenv import load_dotenv
import os
import json
from collections import Counter

load_dotenv()
from supabase import create_client

sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Get ALL legacy stocks
result = sb.table('sniper_signals').select('*').eq('portfolio', 'LEGACY').execute()
stocks = result.data

print(f"Total Legacy stocks: {len(stocks)}")
print("\n" + "="*80)

# ANALYSIS 1: Check unique lens score combinations
print("ANALYSIS 1: Unique Lens Score Combinations")
print("="*80)

def get_lens(stock):
    lens = stock.get('lens_scores', {}) or {}
    if not lens or all(v == 0 for v in lens.values()):
        raw = stock.get('raw_features', {}) or {}
        lens = raw.get('lens_scores', {}) or {}
    return lens

lens_combos = []
for s in stocks:
    lens = get_lens(s)
    h = int(lens.get('HUNTER', 0) or 0)
    c = int(lens.get('CHARTIST', 0) or 0)
    q = int(lens.get('QUANT', 0) or 0)
    o = int(lens.get('ORACLE', 0) or 0)
    combo = f"H:{h} C:{c} Q:{q} O:{o}"
    lens_combos.append(combo)

combo_counts = Counter(lens_combos)
print(f"\nFound {len(combo_counts)} unique combinations out of {len(stocks)} stocks:")
for combo, count in combo_counts.most_common(10):
    print(f"  {combo}: {count} stocks ({count/len(stocks)*100:.1f}%)")

# ANALYSIS 2: Check when stocks were added (date range)
print("\n" + "="*80)
print("ANALYSIS 2: When were these stocks added?")
print("="*80)

dates = [s.get('created_at', '')[:10] for s in stocks if s.get('created_at')]
date_counts = Counter(dates)
print(f"\nDate range: {min(dates)} to {max(dates)}")
print(f"\nStocks per day (top 10):")
for date, count in date_counts.most_common(10):
    print(f"  {date}: {count} stocks")

# ANALYSIS 3: Check if lens_scores column even has data
print("\n" + "="*80)
print("ANALYSIS 3: Where is lens data stored?")
print("="*80)

lens_in_column = 0
lens_in_raw = 0
no_lens = 0

for s in stocks:
    direct_lens = s.get('lens_scores', {}) or {}
    raw = s.get('raw_features', {}) or {}
    raw_lens = raw.get('lens_scores', {}) or {}
    
    if direct_lens and any(v != 0 for v in direct_lens.values()):
        lens_in_column += 1
    elif raw_lens and any(v != 0 for v in raw_lens.values()):
        lens_in_raw += 1
    else:
        no_lens += 1

print(f"  Lens in 'lens_scores' column: {lens_in_column}")
print(f"  Lens in 'raw_features.lens_scores': {lens_in_raw}")
print(f"  No lens data found: {no_lens}")

# ANALYSIS 4: Look at raw_features structure
print("\n" + "="*80)
print("ANALYSIS 4: Sample raw_features structure")
print("="*80)

sample = stocks[0]
raw = sample.get('raw_features', {}) or {}
print(f"\nSample ticker: {sample['ticker']}")
print(f"Keys in raw_features: {list(raw.keys())}")

if 'lens_scores' in raw:
    print(f"\nlens_scores: {json.dumps(raw['lens_scores'], indent=2)}")

if 'weights_used' in raw:
    print(f"\nweights_used: {json.dumps(raw['weights_used'], indent=2)}")

# ANALYSIS 5: Check confidence_score distribution
print("\n" + "="*80)
print("ANALYSIS 5: Confidence Score Distribution")
print("="*80)

scores = [s.get('confidence_score', 0) for s in stocks if s.get('confidence_score')]
if scores:
    print(f"  Min: {min(scores):.1f}")
    print(f"  Max: {max(scores):.1f}")
    print(f"  Avg: {sum(scores)/len(scores):.1f}")
    
    # Bucket them
    buckets = Counter([int(s/10)*10 for s in scores])
    print("\n  Score buckets:")
    for bucket in sorted(buckets.keys()):
        print(f"    {bucket}-{bucket+9}: {buckets[bucket]} stocks")
