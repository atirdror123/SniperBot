"""
Layer 3: Self-Learning Core (Sentient Brain) - MULTI-PERIOD

Implements:
- Epsilon-greedy weight selection for exploration
- PROPORTIONAL gradient descent (lens-specific adjustment)
- MULTI-PERIOD tracking (10, 20, 30, 40, 50, 60 days)
- Weighted aggregate scoring (recent periods matter more)
"""
import os
from datetime import datetime
from supabase import create_client, Client
from primitives import MarketRegime, Lens
from typing import Dict, Optional
import random
from scan_logger import get_logger

logger = get_logger("SENTIENT_BRAIN")

# Review periods in days
REVIEW_PERIODS = [10, 20, 30, 40, 50, 60]

# Weights for each period (more recent = less weight, final = most weight)
# This gives more importance to sustained performance
PERIOD_WEIGHTS = {
    10: 0.10,   # Early signal - low weight
    20: 0.15,
    30: 0.20,
    40: 0.20,
    50: 0.15,
    60: 0.20    # Final outcome - high weight
}


class SentientBrain:
    """
    Advanced self-learning core with multi-period tracking.
    
    Key features:
    - Tracks outcomes at 6 checkpoints (10d to 60d)
    - Each outcome is stored separately (no overwriting)
    - Weight adjustments use weighted average of all outcomes
    - Proportional gradient descent per lens
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
        self.base_learning_rate = 0.02  # Reduced since we learn 6x per stock
        self.epsilon = 0.10             # Exploration rate (10% random weights)
        self.min_weight = 0.3           # Minimum weight value
        self.max_weight = 2.0           # Maximum weight value
        
        # Outcome thresholds
        self.win_threshold = 0.10       # +10% = WIN
        self.loss_threshold = -0.05     # -5% = LOSS

    def get_weights(self, regime: MarketRegime) -> Dict[Lens, float]:
        """Retrieves dynamic weights for the current market regime."""
        # Exploration: 10% of the time, try random weights
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

    def log_period_outcome(self, memory_id: int, outcome_pct: float, regime: str,
                           lens_scores: Dict[str, float], period: int):
        """
        Logs outcome for a SPECIFIC period (10, 20, 30, 40, 50, or 60 days).
        Does NOT overwrite other periods.
        
        Args:
            memory_id: ID of the sentient_memory entry
            outcome_pct: Percentage gain/loss
            regime: Market regime at entry time
            lens_scores: Dict of lens scores
            period: Days since entry (10, 20, 30, 40, 50, or 60)
        """
        if not self.supabase:
            return
            
        if period not in REVIEW_PERIODS:
            logger.warning(f"Invalid period {period}. Must be one of {REVIEW_PERIODS}")
            return

        # Classify outcome
        if outcome_pct >= self.win_threshold:
            outcome_label = "WIN"
            direction = 1
        elif outcome_pct <= self.loss_threshold:
            outcome_label = "LOSS"
            direction = -1
        else:
            outcome_label = "HOLD"
            direction = 0
        
        logger.info(f"[{period}D] {outcome_pct*100:+.1f}% -> {outcome_label}")

        # Update the specific period columns
        outcome_col = f"outcome_{period}d"
        pct_col = f"pct_{period}d"
        
        try:
            self.supabase.table("sentient_memory").update({
                outcome_col: outcome_label,
                pct_col: outcome_pct
            }).eq("id", memory_id).execute()
        except Exception as e:
            logger.error(f"Failed to update {outcome_col}: {e}")
            return

        # Skip weight adjustment for HOLD
        if direction == 0:
            return

        # Adjust weights with period-specific weighting
        period_weight = PERIOD_WEIGHTS.get(period, 0.15)
        self._adjust_weights(regime, lens_scores, direction, period_weight, outcome_pct, period)

    def _adjust_weights(self, regime: str, lens_scores: Dict[str, float], 
                        direction: int, period_weight: float, outcome_pct: float, period: int):
        """Applies proportional gradient descent weight adjustment."""
        
        # Calculate proportional contributions
        total_score = sum(lens_scores.values())
        if total_score == 0:
            return
        
        proportions = {lens: score / total_score for lens, score in lens_scores.items()}
        
        # Scale by outcome magnitude (capped at 2x)
        magnitude_scale = min(abs(outcome_pct) / 0.10, 2.0)
        
        # Get current weights
        try:
            response = self.supabase.table("lens_weights").select("*").eq("regime", regime).execute()
            if not response.data:
                return
            
            current = response.data[0]
            
            # Calculate adjustments (scaled by period weight)
            adjustments = {}
            for lens, proportion in proportions.items():
                adj = direction * self.base_learning_rate * proportion * magnitude_scale * period_weight
                adjustments[lens] = adj
            
            # Apply adjustments
            new_weights = {
                "w_quant": self._clamp(current["w_quant"] + adjustments.get("QUANT", 0)),
                "w_oracle": self._clamp(current["w_oracle"] + adjustments.get("ORACLE", 0)),
                "w_hunter": self._clamp(current["w_hunter"] + adjustments.get("HUNTER", 0)),
                "w_chartist": self._clamp(current["w_chartist"] + adjustments.get("CHARTIST", 0)),
                "updated_at": datetime.now().isoformat()
            }
            
            self.supabase.table("lens_weights").update(new_weights).eq("regime", regime).execute()
            
            # Log to history
            history_entry = {
                "regime": regime,
                "w_quant": new_weights["w_quant"],
                "w_oracle": new_weights["w_oracle"],
                "w_hunter": new_weights["w_hunter"],
                "w_chartist": new_weights["w_chartist"],
                "reason": f"@{period}D: {outcome_pct*100:+.1f}% (pw={period_weight:.2f})"
            }
            self.supabase.table("weight_history").insert(history_entry).execute()
            
            logger.info(f"Weights adjusted for {regime} @{period}D")
            
        except Exception as e:
            logger.error(f"Failed to adjust weights: {e}")

    def _clamp(self, value: float) -> float:
        """Clamps weight value to valid range."""
        return max(self.min_weight, min(self.max_weight, value))
