"""
Tournament AI - Risk Manager

Uses AI (Gemini) to ruthlessly analyze and rank stock candidates.
Acts as a "Risk Manager at a top Hedge Fund" - finds reasons NOT to buy.
Reduces ~10-15 pressure cooker candidates to exactly 3 "Sniper" picks.
"""
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

# Configure Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


RISK_MANAGER_PROMPT = """You are a RUTHLESS Risk Manager at a top Hedge Fund.

Your job is to FIND REASONS NOT TO BUY. You are extremely skeptical and conservative.
Only the absolute best setups deserve our capital.

## Your Task:
Analyze these {num_candidates} stock candidates and select EXACTLY 3 for our portfolio.

## Candidate Data:
{candidates_json}

## Analysis Framework:

### For EACH stock, evaluate:
1. **Technical Risk** (40% weight)
   - Is RSI in the danger zone (>75 = overbought)?
   - Is the daily move too extreme (>8% = likely to reverse)?
   - Is RVOL suspicious (could be end-of-move exhaustion)?

2. **Volume Catalyst** (30% weight)
   - Is this real institutional buying or retail FOMO?
   - Is volume sustainable or one-day spike?

3. **Blue Sky Potential** (30% weight)
   - How close to 52-week high?
   - Is there resistance ahead?

### RED FLAGS (Automatic Disqualification):
- Daily change >10% (too extended)
- RSI >80 (extreme overbought)
- RVOL >5x with small cap (pump risk)

## Output Format:
Return a JSON object with EXACTLY this structure:
{{
    "analysis": [
        {{
            "ticker": "SYMBOL",
            "verdict": "SELECTED" or "REJECTED",
            "risk_score": 1-10 (10 = highest risk),
            "reason": "One sentence explanation"
        }}
    ],
    "top_3": [
        {{
            "rank": 1,
            "ticker": "SYMBOL",
            "confidence": 1-100,
            "entry_reason": "Why this is a good trade"
        }}
    ]
}}

BE RUTHLESS. Most candidates should be REJECTED.
Only select stocks with risk_score <= 4.
"""


def run_tournament(candidates: list) -> dict:
    """
    Run the Tournament AI to select top 3 from candidates.
    
    Args:
        candidates: List of dicts with ticker, rsi, rvol, daily_change, etc.
    
    Returns:
        Dict with analysis and top_3 selections
    """
    if not GOOGLE_API_KEY:
        print("⚠️ GOOGLE_API_KEY not set. Falling back to score-based selection.")
        return fallback_selection(candidates)
    
    if len(candidates) <= 3:
        # If we have 3 or fewer, just return them all
        return {
            "top_3": [
                {"rank": i+1, "ticker": c['ticker'], "confidence": 80, "entry_reason": "Passed all filters"}
                for i, c in enumerate(candidates)
            ]
        }
    
    # Prepare candidate data for AI
    candidates_json = json.dumps([
        {
            "ticker": c['ticker'],
            "rsi": round(c.get('rsi', 0), 1),
            "rvol": round(c.get('rvol', 0), 2),
            "daily_change_pct": round(c.get('daily_change', 0), 2),
            "pct_from_52w_high": round(c.get('pct_from_high', 0), 1),
            "price": round(c.get('price', 0), 2),
            "ema_aligned": c.get('ema_aligned', True)
        }
        for c in candidates
    ], indent=2)
    
    # Build prompt
    prompt = RISK_MANAGER_PROMPT.format(
        num_candidates=len(candidates),
        candidates_json=candidates_json
    )
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,  # Lower = more consistent
                "max_output_tokens": 2000
            }
        )
        
        # Parse response
        response_text = response.text
        
        # Extract JSON from response
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_str = response_text[json_start:json_end].strip()
        else:
            json_str = response_text.strip()
        
        result = json.loads(json_str)
        
        print("\n🤖 TOURNAMENT AI RESULTS:")
        print("-" * 40)
        
        for item in result.get('analysis', []):
            emoji = "✅" if item['verdict'] == 'SELECTED' else "❌"
            print(f"  {emoji} {item['ticker']}: {item['verdict']} (Risk: {item['risk_score']}/10)")
            print(f"     {item['reason']}")
        
        print("\n🎯 TOP 3 SELECTIONS:")
        for pick in result.get('top_3', []):
            print(f"  #{pick['rank']} {pick['ticker']} (Confidence: {pick['confidence']}%)")
            print(f"     {pick['entry_reason']}")
        
        return result
        
    except Exception as e:
        print(f"⚠️ AI Tournament failed: {e}")
        return fallback_selection(candidates)


def fallback_selection(candidates: list) -> dict:
    """Fallback to score-based selection if AI fails."""
    print("Using fallback score-based selection...")
    
    # Sort by composite score if available, otherwise by RVOL
    sorted_candidates = sorted(
        candidates,
        key=lambda x: x.get('composite_score', x.get('rvol', 0)),
        reverse=True
    )[:3]
    
    return {
        "top_3": [
            {
                "rank": i+1,
                "ticker": c['ticker'],
                "confidence": 70,
                "entry_reason": f"RVOL: {c.get('rvol', 0):.1f}x, RSI: {c.get('rsi', 0):.0f}"
            }
            for i, c in enumerate(sorted_candidates)
        ]
    }


if __name__ == "__main__":
    # Test with sample candidates
    test_candidates = [
        {"ticker": "AAPL", "rsi": 65, "rvol": 1.8, "daily_change": 3.5, "pct_from_high": 97, "price": 185.50},
        {"ticker": "NVDA", "rsi": 72, "rvol": 2.5, "daily_change": 5.2, "pct_from_high": 99, "price": 520.00},
        {"ticker": "AMD", "rsi": 58, "rvol": 1.6, "daily_change": 2.8, "pct_from_high": 92, "price": 145.00},
        {"ticker": "MSFT", "rsi": 68, "rvol": 1.4, "daily_change": 2.1, "pct_from_high": 95, "price": 405.00},
        {"ticker": "TSLA", "rsi": 78, "rvol": 3.2, "daily_change": 7.5, "pct_from_high": 88, "price": 245.00}
    ]
    
    result = run_tournament(test_candidates)
    print("\n✅ Tournament complete!")
