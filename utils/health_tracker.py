"""
Exchange Health Tracker
======================
Tracks exchange API reliability and health over time.
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple
from datetime import datetime


class ExchangeHealthTracker:
    """
    Tracks exchange API success/failure rates and provides health scores.
    """
    
    def __init__(self):
        """Initialize the health tracker."""
        # Format: exchange_name -> [(timestamp, success), ...]
        self.history: Dict[str, List[Tuple[float, bool]]] = defaultdict(list)
        self.max_history_hours = 24  # Keep 24 hours of history
    
    def record_result(self, exchange_name: str, success: bool) -> None:
        """
        Record an API call result for an exchange.
        
        Args:
            exchange_name: Name of the exchange
            success: Whether the API call succeeded
        """
        now = time.time()
        self.history[exchange_name].append((now, success))
        
        # Clean old history
        self._clean_old_history(exchange_name)
    
    def get_health_score(self, exchange_name: str) -> float:
        """
        Get health score for an exchange (0-100).
        
        Args:
            exchange_name: Name of the exchange
            
        Returns:
            Health score from 0 (terrible) to 100 (perfect)
        """
        if exchange_name not in self.history:
            return 100.0  # No failures yet
        
        recent_history = self.history[exchange_name]
        if not recent_history:
            return 100.0
        
        # Calculate success rate from recent history
        total_calls = len(recent_history)
        successful_calls = sum(1 for _, success in recent_history if success)
        
        if total_calls == 0:
            return 100.0
        
        success_rate = successful_calls / total_calls
        return success_rate * 100
    
    def is_exchange_healthy(self, exchange_name: str, min_score: float = 50.0) -> bool:
        """
        Check if an exchange is considered healthy.
        
        Args:
            exchange_name: Name of the exchange
            min_score: Minimum health score to be considered healthy
            
        Returns:
            True if exchange is healthy, False otherwise
        """
        return self.get_health_score(exchange_name) >= min_score
    
    def get_all_health_scores(self) -> Dict[str, float]:
        """
        Get health scores for all tracked exchanges.
        
        Returns:
            Dictionary mapping exchange names to health scores
        """
        return {
            exchange: self.get_health_score(exchange)
            for exchange in self.history.keys()
        }
    
    def get_health_report(self) -> str:
        """
        Get a formatted health report for all exchanges.
        
        Returns:
            Formatted health report string
        """
        if not self.history:
            return "No exchange health data available"
        
        lines = ["Exchange Health Report:"]
        lines.append("-" * 30)
        
        for exchange, score in self.get_all_health_scores().items():
            status = "🟢 HEALTHY" if score >= 80 else "🟡 WARNING" if score >= 50 else "🔴 UNHEALTHY"
            lines.append(f"{exchange:.<15} {score:>5.1f}% {status}")
        
        return "\n".join(lines)
    
    def _clean_old_history(self, exchange_name: str) -> None:
        """Remove history older than max_history_hours."""
        if exchange_name not in self.history:
            return
        
        cutoff_time = time.time() - (self.max_history_hours * 3600)
        self.history[exchange_name] = [
            (timestamp, success) 
            for timestamp, success in self.history[exchange_name]
            if timestamp > cutoff_time
        ]


# Global health tracker instance
_global_tracker = ExchangeHealthTracker()


def record_exchange_result(exchange_name: str, success: bool) -> None:
    """
    Record an exchange API result in the global tracker.
    
    Args:
        exchange_name: Name of the exchange
        success: Whether the API call succeeded
    """
    _global_tracker.record_result(exchange_name, success)


def get_exchange_health_score(exchange_name: str) -> float:
    """
    Get health score for an exchange.
    
    Args:
        exchange_name: Name of the exchange
        
    Returns:
        Health score from 0-100
    """
    return _global_tracker.get_health_score(exchange_name)


def get_health_report() -> str:
    """
    Get formatted health report for all exchanges.
    
    Returns:
        Formatted health report string
    """
    return _global_tracker.get_health_report()


def is_exchange_healthy(exchange_name: str) -> bool:
    """
    Check if an exchange is healthy.
    
    Args:
        exchange_name: Name of the exchange
        
    Returns:
        True if healthy, False otherwise
    """
    return _global_tracker.is_exchange_healthy(exchange_name)