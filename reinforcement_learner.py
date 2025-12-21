import os
from supabase import create_client, Client
from primitives import MarketRegime, Lens
from typing import Dict, List
import random

class SentientBrain:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if url and key:
            self.supabase = create_client(url, key)
        else:
            self.supabase = None
            print("[BRAIN] WARNING: Supabase not connected. Using default static weights.")
            
        self.learning_rate = 0.05
        self.epsilon = 0.10 # Exploration rate (10% random weights)

    def get_weights(self, regime: MarketRegime) -> Dict[Lens, float]:
        """
        Layer 3: The Sentient Core.
        Retrieves dynamic weights for the current market regime.
        Implements Epsilon-Greedy exploration.
        """
        # Exploration: 10% of the time, try random weights to discover new edges
        if random.random() < self.epsilon:
            print("[BRAIN] Epsilon Triggered: Exploring randomized weights.")
            return {
                Lens.QUANT: random.uniform(0.5, 1.5),
                Lens.ORACLE: random.uniform(0.5, 1.5),
                Lens.HUNTER: random.uniform(0.5, 1.5),
                Lens.CHARTIST: random.uniform(0.5, 1.5),
            }

        # Exploitation: Get the best known weights from DB
        if self.supabase:
            try:
                response = self.supabase.table('lens_weights').select('*').eq('regime', regime.value).execute()
                if response.data:
                    row = response.data[0]
                    return {
                        Lens.QUANT: row['w_quant'],
                        Lens.ORACLE: row['w_oracle'],
                        Lens.HUNTER: row['w_hunter'],
                        Lens.CHARTIST: row['w_chartist']
                    }
            except Exception as e:
                print(f"[BRAIN] Error fetching weights: {e}", flush=True)

        # Default Fallback (if DB fails or not connected)
        regime_defaults = {
            MarketRegime.BULL: {Lens.QUANT: 1.0, Lens.ORACLE: 1.0, Lens.HUNTER: 1.2, Lens.CHARTIST: 1.0},
            MarketRegime.BEAR: {Lens.QUANT: 1.2, Lens.ORACLE: 1.0, Lens.HUNTER: 0.8, Lens.CHARTIST: 1.0},
            MarketRegime.CHOP: {Lens.QUANT: 0.8, Lens.ORACLE: 0.8, Lens.HUNTER: 0.8, Lens.CHARTIST: 1.5},
        }
        return regime_defaults.get(regime, regime_defaults[MarketRegime.CHOP])

    def log_outcome(self, ticker: str, outcome_label: str, attribution: Dict[Lens, float]):
        """
        The Feedback Loop.
        Updates weights based on success/failure.
        
        Refines the weight of the Lenses that contributed most to the score.
        """
        # Note: In a real system, this runs 20/90 days later.
        # This function would be called by a 'Nightly Review' job.
        # For now, we just log the logic.
        print(f"[BRAIN] Learning from {ticker} -> {outcome_label}")
        
        if not self.supabase:
            return

        # Simple Gradient Descent logic:
        # If WIN: Increase weights of high-scoring lenses.
        # If LOSS: Decrease weights of high-scoring lenses (they gave false confidence).
        
        pass # To fully implement, we need to read current weights, adjust, and update DB.
