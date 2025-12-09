from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, List
from datetime import datetime

class MarketRegime(Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    CHOP = "CHOP"

class Lens(Enum):
    QUANT = "QUANT"     # Lens A
    ORACLE = "ORACLE"   # Lens B
    HUNTER = "HUNTER"   # Lens C
    CHARTIST = "CHARTIST" # Lens D

@dataclass
class LensScore:
    lens: Lens
    score: float # 0.0 to 100.0
    weight: float # Dynamic weight assigned by RL
    details: Dict[str, any] = field(default_factory=dict)
    
    @property
    def weighted_score(self) -> float:
        return self.score * self.weight

@dataclass
class StockSetup:
    ticker: str
    timestamp: datetime
    final_score: float
    regime: MarketRegime
    lens_scores: Dict[Lens, LensScore]
    
    # Fundamental/Technical Metadata
    price: float
    volume: float
    sector: str
    
    # Integration Metadata
    is_valid: bool = False
    rejection_reason: Optional[str] = None

class SafetyStatus(Enum):
    SAFE = "SAFE"       # All systems go
    CAUTION = "CAUTION" # Reduced sizing
    ANGER = "ANGER"     # Cash only (Kill switch)
