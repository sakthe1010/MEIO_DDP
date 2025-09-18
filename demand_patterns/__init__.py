from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import random

class DemandPattern(ABC):
    """Base class for all demand patterns"""
    
    @abstractmethod
    def sample(self, t: int) -> float:
        """Sample demand for time period t"""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Get the parameters that define this demand pattern"""
        pass
