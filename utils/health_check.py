"""
Health Check System
==================
Provides simple health check functionality for the exchange system.
"""

import json
import time
from typing import Dict, Any
from utils.health_tracker import _global_tracker


def get_system_health() -> Dict[str, Any]:
    """
    Get comprehensive system health information.
    
    Returns:
        Dictionary with system health data
    """
    exchange_scores = _global_tracker.get_all_health_scores()
    
    # Calculate overall system health
    if exchange_scores:
        overall_health = sum(exchange_scores.values()) / len(exchange_scores)
        status = "healthy" if overall_health >= 80 else "warning" if overall_health >= 50 else "unhealthy"
    else:
        overall_health = 100.0
        status = "healthy"
    
    return {
        "status": status,
        "overall_score": round(overall_health, 1),
        "exchanges": {
            name: {
                "score": round(score, 1),
                "status": "healthy" if score >= 80 else "warning" if score >= 50 else "unhealthy"
            }
            for name, score in exchange_scores.items()
        },
        "timestamp": int(time.time())
    }


def get_health_json() -> str:
    """
    Get system health as JSON string.
    
    Returns:
        JSON string with health information
    """
    return json.dumps(get_system_health(), indent=2)


def print_health_status() -> None:
    """Print a simple health status to console."""
    health = get_system_health()
    
    print(f"\nSystem Health: {health['status'].upper()} ({health['overall_score']}/100)")
    
    if health['exchanges']:
        print("Exchange Status:")
        for name, info in health['exchanges'].items():
            status_symbol = "OK" if info['status'] == "healthy" else "WARN" if info['status'] == "warning" else "FAIL"
            print(f"  [{status_symbol}] {name}: {info['score']}/100")
    else:
        print("  No exchange data available")


if __name__ == "__main__":
    # Simple health check when run directly
    print_health_status()