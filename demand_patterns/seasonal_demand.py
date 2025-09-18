from typing import Dict, Any, List, Optional
import random
import math
from . import DemandPattern

class SeasonalDemand(DemandPattern):
    """
    Seasonal demand pattern with base demand and seasonal factors
    """
    def __init__(self, 
                 base_demand: float,
                 seasonal_factors: List[float],
                 noise_std: float = 0.0,
                 seed: Optional[int] = None):
        """
        Parameters:
        -----------
        base_demand : float
            Base demand level
        seasonal_factors : List[float]
            Multiplicative seasonal factors. Length determines season length.
        noise_std : float
            Standard deviation of random noise to add
        seed : Optional[int]
            Random seed for noise generation
        """
        self.base_demand = base_demand
        self.seasonal_factors = seasonal_factors
        self.noise_std = noise_std
        self.rng = random.Random(seed)

    def sample(self, t: int) -> float:
        season_idx = t % len(self.seasonal_factors)
        seasonal = self.base_demand * self.seasonal_factors[season_idx]
        
        if self.noise_std > 0:
            noise = self.rng.gauss(0, self.noise_std)
            return max(0, seasonal + noise)
        return seasonal

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "seasonal",
            "base_demand": self.base_demand,
            "seasonal_factors": self.seasonal_factors,
            "noise_std": self.noise_std
        }

class TrendSeasonalDemand(DemandPattern):
    """
    Demand pattern with trend and seasonality
    """
    def __init__(self,
                 initial_demand: float,
                 trend_factor: float,
                 seasonal_factors: List[float],
                 noise_std: float = 0.0,
                 seed: Optional[int] = None):
        """
        Parameters:
        -----------
        initial_demand : float
            Starting demand level
        trend_factor : float
            Per-period multiplicative trend factor (1.0 = no trend)
        seasonal_factors : List[float]
            Multiplicative seasonal factors
        noise_std : float
            Standard deviation of random noise
        seed : Optional[int]
            Random seed for noise generation
        """
        self.initial_demand = initial_demand
        self.trend_factor = trend_factor
        self.seasonal_factors = seasonal_factors
        self.noise_std = noise_std
        self.rng = random.Random(seed)

    def sample(self, t: int) -> float:
        # Calculate trend component
        trend = self.initial_demand * (self.trend_factor ** t)
        
        # Apply seasonality
        season_idx = t % len(self.seasonal_factors)
        seasonal = trend * self.seasonal_factors[season_idx]
        
        # Add noise if specified
        if self.noise_std > 0:
            noise = self.rng.gauss(0, self.noise_std)
            return max(0, seasonal + noise)
        return seasonal

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "trend_seasonal",
            "initial_demand": self.initial_demand,
            "trend_factor": self.trend_factor,
            "seasonal_factors": self.seasonal_factors,
            "noise_std": self.noise_std
        }
