"""
AI Queue Worker
================
Background worker that processes the AI job queue.
Run this as a scheduled task or cron job.

Usage:
    python ai_queue_worker.py          # Process up to 10 jobs
    python ai_queue_worker.py --loop   # Continuous processing (for cron)
"""
import argparse
import time
from datetime import datetime
from ai_signal_engine import AISignalEngine


def main():
    parser = argparse.ArgumentParser(description='AI Queue Worker')
    parser.add_argument('--loop', action='store_true', help='Continuous loop mode')
    parser.add_argument('--max-jobs', type=int, default=10, help='Max jobs per run')
    args = parser.parse_args()
    
    engine = AISignalEngine()
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] AI Queue Worker Started")
    print(f"Mode: {'Continuous Loop' if args.loop else 'Single Run'}")
    print(f"Max Jobs: {args.max_jobs}")
    print("=" * 50)
    
    if args.loop:
        # Continuous mode - process forever
        while True:
            try:
                engine.process_queue(max_jobs=args.max_jobs)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sleeping 60s...")
                time.sleep(60)
            except KeyboardInterrupt:
                print("\nShutting down...")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(60)
    else:
        # Single run mode
        engine.process_queue(max_jobs=args.max_jobs)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Worker finished")


if __name__ == "__main__":
    main()
