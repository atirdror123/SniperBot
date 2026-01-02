"""
Layer 3: Self-Learning Core (Sentient Brain)

Implements:
- Epsilon-greedy weight selection for exploration
- Gradient descent weight adjustment based on outcomes
- Logging of weight changes to weight_history
"""
import os
from datetime import datetime
from supabase import create_client, Client
from primitives import MarketRegime, Lens
from typing import Dict, Optional
import random
from scan_logger import get_logger

logger = get_logger("SENTIENT_BRAIN")


class SentientBrain:
    """
    The self-learning core that adjusts lens weights based on stock outcomes.
    """
    
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if url and key:
            self.supabase = create_client(url, key)
        else:
            self.supabase = None
            logger.warning("Supabase not connected. Using default static weights.")
        
        # Learning hyperparameters
        self.learning_rate = 0.05  # How much to adjust weights per outcome
        self.epsilon = 0.10        # Exploration rate (10% random weights)
        self.min_weight = 0.5      # Minimum weight value
        self.max_weight = 1.5      # Maximum weight value

    def get_weights(self, regime: MarketRegime) -> Dict[Lens, float]:
        """
        Retrieves dynamic weights for the current market regime.
        Implements Epsilon-Greedy exploration.
        """
        # Exploration: 10% of the time, try random weights to discover new edges
        if random.random() < self.epsilon:
            logger.info("Epsilon Triggered: Exploring randomized weights.")
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
                logger.error(f"Error fetching weights: {e}")

        # Default Fallback
        regime_defaults = {
            MarketRegime.BULL: {Lens.QUANT: 1.0, Lens.ORACLE: 1.0, Lens.HUNTER: 1.2, Lens.CHARTIST: 1.0},
            MarketRegime.BEAR: {Lens.QUANT: 1.2, Lens.ORACLE: 1.0, Lens.HUNTER: 0.8, Lens.CHARTIST: 1.0},
            MarketRegime.CHOP: {Lens.QUANT: 0.8, Lens.ORACLE: 0.8, Lens.HUNTER: 0.8, Lens.CHARTIST: 1.5},
        }
        return regime_defaults.get(regime, regime_defaults[MarketRegime.CHOP])

    def log_outcome(self, memory_id: int, outcome_pct: float, regime: str):
        """
        Updates weights based on stock outcome using gradient descent.
        
        Args:
            memory_id: ID of the sentient_memory entry
            outcome_pct: Percentage gain/loss (e.g., 0.15 for +15%, -0.05 for -5%)
            regime: Market regime at entry time (BULL, BEAR, CHOP)
        """
        if not self.supabase:
            logger.warning("Supabase not connected. Cannot log outcome.")
            return

        # Classify outcome
        if outcome_pct >= 0.10:
            outcome_label = "WIN"
            adjustment = self.learning_rate  # Increase weights
        elif outcome_pct <= -0.05:
            outcome_label = "LOSS"
            adjustment = -self.learning_rate  # Decrease weights
        else:
            outcome_label = "HOLD"
            adjustment = 0  # No change
        
        logger.info(f"Processing outcome: {outcome_pct*100:.1f}% -> {outcome_label}")

        # Update sentient_memory record
        try:
            self.supabase.table("sentient_memory").update({
                "outcome_label": outcome_label,
                "outcome_pct": outcome_pct,
                "reviewed_at": datetime.now().isoformat()
            }).eq("id", memory_id).execute()
        except Exception as e:
            logger.error(f"Failed to update sentient_memory: {e}")
            return

        # Skip weight update if HOLD
        if adjustment == 0:
            return

        # Get current weights
        try:
            response = self.supabase.table("lens_weights").select("*").eq("regime", regime).execute()
            if not response.data:
                logger.error(f"No weights found for regime {regime}")
                return
            
            current = response.data[0]
            
            # Apply gradient descent adjustment
            new_weights = {
                "w_quant": self._clamp(current["w_quant"] + adjustment),
                "w_oracle": self._clamp(current["w_oracle"] + adjustment),
                "w_hunter": self._clamp(current["w_hunter"] + adjustment),
                "w_chartist": self._clamp(current["w_chartist"] + adjustment),
                "updated_at": datetime.now().isoformat()
            }
            
            # Update weights
            self.supabase.table("lens_weights").update(new_weights).eq("regime", regime).execute()
            
            # Log to history
            history_entry = {
                "regime": regime,
                "w_quant": new_weights["w_quant"],
                "w_oracle": new_weights["w_oracle"],
                "w_hunter": new_weights["w_hunter"],
                "w_chartist": new_weights["w_chartist"],
                "reason": f"{outcome_label}: {outcome_pct*100:.1f}%"
            }
            self.supabase.table("weight_history").insert(history_entry).execute()
            
            logger.info(f"Weights updated for {regime}: {new_weights}")
            
        except Exception as e:
            logger.error(f"Failed to update weights: {e}")

    def _clamp(self, value: float) -> float:
        """Clamps weight value to valid range."""
        return max(self.min_weight, min(self.max_weight, value))
