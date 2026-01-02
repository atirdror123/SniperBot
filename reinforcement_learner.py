"""
Layer 3: Self-Learning Core (Sentient Brain) - ADVANCED

Implements:
- Epsilon-greedy weight selection for exploration
- PROPORTIONAL gradient descent (lens-specific adjustment)
- Multi-period review (10, 20, 30 days)
- Weight history logging with detailed attribution
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
    Advanced self-learning core with proportional gradient descent.
    
    Key features:
    - Adjusts each lens weight proportionally to its contribution
    - High-scoring lenses get more credit for wins, more blame for losses
    - Low-scoring lenses are adjusted less
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
        self.base_learning_rate = 0.03  # Base rate before proportional scaling
        self.epsilon = 0.10             # Exploration rate (10% random weights)
        self.min_weight = 0.3           # Minimum weight value
        self.max_weight = 2.0           # Maximum weight value
        
        # Outcome thresholds
        self.win_threshold = 0.10       # +10% = WIN
        self.loss_threshold = -0.05     # -5% = LOSS

    def get_weights(self, regime: MarketRegime) -> Dict[Lens, float]:
        """
        Retrieves dynamic weights for the current market regime.
        Implements Epsilon-Greedy exploration.
        """
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

    def log_outcome(self, memory_id: int, outcome_pct: float, regime: str, 
                    lens_scores: Dict[str, float], review_period: int = 20):
        """
        PROPORTIONAL Gradient Descent Weight Adjustment.
        
        Args:
            memory_id: ID of the sentient_memory entry
            outcome_pct: Percentage gain/loss (e.g., 0.15 for +15%)
            regime: Market regime at entry time (BULL, BEAR, CHOP)
            lens_scores: Dict of lens scores {"QUANT": 80, "ORACLE": 60, ...}
            review_period: Days since entry (10, 20, or 30)
        
        How it works:
            - Each lens is adjusted proportionally to its contribution
            - If HUNTER=90 and ORACLE=60, HUNTER gets 90/(90+60) = 60% of the adjustment
            - WIN: High-scoring lenses get credit → weight increases
            - LOSS: High-scoring lenses get blame → weight decreases
        """
        if not self.supabase:
            logger.warning("Supabase not connected. Cannot log outcome.")
            return

        # Classify outcome
        if outcome_pct >= self.win_threshold:
            outcome_label = "WIN"
            direction = 1  # Increase weights
        elif outcome_pct <= self.loss_threshold:
            outcome_label = "LOSS"
            direction = -1  # Decrease weights
        else:
            outcome_label = "HOLD"
            direction = 0  # No change
        
        logger.info(f"[{review_period}D] Processing: {outcome_pct*100:.1f}% -> {outcome_label}")

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
        if direction == 0:
            return

        # Calculate proportional adjustments
        total_score = sum(lens_scores.values())
        if total_score == 0:
            logger.warning("Total lens score is 0. Cannot calculate proportions.")
            return
        
        # Proportional contribution of each lens
        proportions = {
            lens: score / total_score 
            for lens, score in lens_scores.items()
        }
        
        # Scale adjustment by outcome magnitude (bigger win/loss = more learning)
        magnitude_scale = min(abs(outcome_pct) / 0.10, 2.0)  # Cap at 2x for extreme moves
        
        # Get current weights
        try:
            response = self.supabase.table("lens_weights").select("*").eq("regime", regime).execute()
            if not response.data:
                logger.error(f"No weights found for regime {regime}")
                return
            
            current = response.data[0]
            
            # Calculate proportional adjustments for each lens
            adjustments = {}
            for lens, proportion in proportions.items():
                # Higher contributing lens gets larger adjustment
                lens_adjustment = direction * self.base_learning_rate * proportion * magnitude_scale
                adjustments[lens] = lens_adjustment
            
            # Apply adjustments
            new_weights = {
                "w_quant": self._clamp(current["w_quant"] + adjustments.get("QUANT", 0)),
                "w_oracle": self._clamp(current["w_oracle"] + adjustments.get("ORACLE", 0)),
                "w_hunter": self._clamp(current["w_hunter"] + adjustments.get("HUNTER", 0)),
                "w_chartist": self._clamp(current["w_chartist"] + adjustments.get("CHARTIST", 0)),
                "updated_at": datetime.now().isoformat()
            }
            
            # Update weights
            self.supabase.table("lens_weights").update(new_weights).eq("regime", regime).execute()
            
            # Log to history with detailed attribution
            history_entry = {
                "regime": regime,
                "w_quant": new_weights["w_quant"],
                "w_oracle": new_weights["w_oracle"],
                "w_hunter": new_weights["w_hunter"],
                "w_chartist": new_weights["w_chartist"],
                "reason": f"{outcome_label} ({outcome_pct*100:+.1f}%) @{review_period}D | " + 
                          f"Q:{adjustments.get('QUANT', 0):+.3f} O:{adjustments.get('ORACLE', 0):+.3f} " +
                          f"H:{adjustments.get('HUNTER', 0):+.3f} C:{adjustments.get('CHARTIST', 0):+.3f}"
            }
            self.supabase.table("weight_history").insert(history_entry).execute()
            
            logger.info(f"Weights updated for {regime}: Q={new_weights['w_quant']:.3f} O={new_weights['w_oracle']:.3f} "
                       f"H={new_weights['w_hunter']:.3f} C={new_weights['w_chartist']:.3f}")
            
        except Exception as e:
            logger.error(f"Failed to update weights: {e}")

    def _clamp(self, value: float) -> float:
        """Clamps weight value to valid range."""
        return max(self.min_weight, min(self.max_weight, value))
