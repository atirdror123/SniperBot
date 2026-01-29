import time
print("Start", flush=True)
from ai_signal_engine import AISignalEngine
print("Imported", flush=True)

try:
    engine = AISignalEngine()
    print("Engine Created", flush=True)
except Exception as e:
    print(f"Engine failed: {e}", flush=True)

STOCKS = ['NVDA']
print("Loop start", flush=True)
for s in STOCKS:
    print(f"Processing {s}", flush=True)
    try:
        res = engine.score_stock(s)
        print("Score done", flush=True)
    except Exception as e:
        print(f"Score failed: {e}", flush=True)
print("Done", flush=True)
