"""
Real-time Anomaly Detection System

Detects unusual spending patterns and alerts admins.
Uses statistical analysis and ML-ready patterns.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Detect spending anomalies using statistical methods.
    
    Methods:
    - Spike detection (sudden cost increase)
    - Trend detection (gradual increase)
    - Model mismatch detection (wrong model for task)
    - Team anomalies (unusual team behavior)
    """
    
    def __init__(self):
        self.historical_data = []
        self.baseline_window = 7  # days
        self.spike_threshold = 2.0  # std devs above mean
        self.trend_threshold = 1.5  # std devs above mean
    
    def add_data_point(self, timestamp: str, cost: float, team: str, model: str, tokens: int):
        """Add a cost data point for analysis."""
        self.historical_data.append({
            "timestamp": timestamp,
            "cost": cost,
            "team": team,
            "model": model,
            "tokens": tokens,
            "datetime": datetime.fromisoformat(timestamp)
        })
    
    def detect_spike(self, current_cost: float, window_hours: int = 24) -> tuple[bool, dict[str, Any]]:
        """
        Detect sudden cost spike in recent window.
        
        Returns: (is_anomaly, details)
        """
        cutoff_time = datetime.now() - timedelta(hours=window_hours)
        recent_costs = [
            d["cost"] for d in self.historical_data
            if d["datetime"] >= cutoff_time
        ]
        
        if not recent_costs or len(recent_costs) < 5:
            return False, {"reason": "insufficient_data"}
        
        mean_cost = statistics.mean(recent_costs)
        std_cost = statistics.stdev(recent_costs) if len(recent_costs) > 1 else 0
        
        if std_cost == 0:
            return False, {"reason": "no_variance"}
        
        z_score = (current_cost - mean_cost) / std_cost
        
        is_anomaly = z_score > self.spike_threshold
        
        return is_anomaly, {
            "type": "spike",
            "current_cost": current_cost,
            "mean_cost": mean_cost,
            "std_dev": std_cost,
            "z_score": z_score,
            "threshold": self.spike_threshold,
            "severity": "high" if z_score > 3.0 else "medium"
        }
    
    def detect_trend(self, team: str, window_days: int = 7) -> tuple[bool, dict[str, Any]]:
        """
        Detect gradual cost increase trend.
        
        Returns: (is_anomaly, details)
        """
        cutoff_time = datetime.now() - timedelta(days=window_days)
        team_data = [
            d for d in self.historical_data
            if d["team"] == team and d["datetime"] >= cutoff_time
        ]
        
        if not team_data or len(team_data) < 10:
            return False, {"reason": "insufficient_data"}
        
        # Split into first half and second half
        mid_point = len(team_data) // 2
        first_half = [d["cost"] for d in team_data[:mid_point]]
        second_half = [d["cost"] for d in team_data[mid_point:]]
        
        first_mean = statistics.mean(first_half)
        second_mean = statistics.mean(second_half)
        
        # Check if second half is significantly higher
        if first_mean > 0:
            increase_pct = (second_mean - first_mean) / first_mean * 100
        else:
            increase_pct = 0
        
        is_anomaly = increase_pct > 30  # 30% increase
        
        return is_anomaly, {
            "type": "trend",
            "team": team,
            "first_half_avg": first_mean,
            "second_half_avg": second_mean,
            "increase_percent": increase_pct,
            "threshold_percent": 30,
            "severity": "high" if increase_pct > 50 else "medium"
        }
    
    def detect_model_mismatch(self, model: str, tokens: int, cost: float) -> tuple[bool, dict[str, Any]]:
        """
        Detect inefficient model usage (e.g., using GPT-4 for simple tasks).
        
        Returns: (is_anomaly, details)
        """
        # Define model efficiency
        model_lower = model.lower()
        
        # Expensive models that shouldn't be used for small requests
        expensive_models = {
            "gpt-4": 100,  # threshold tokens
            "gpt-4-turbo": 75,
            "claude-3-opus": 50,
            "gemini-1.5-pro": 60,
        }
        
        # Check if expensive model used for small task
        if any(exp_model in model_lower for exp_model in expensive_models):
            threshold = expensive_models.get(
                next((m for m in expensive_models if m in model_lower), "gpt-4"),
                100
            )
            
            if tokens is not None and threshold is not None and tokens < threshold:
                return True, {
                    "type": "model_mismatch",
                    "model": model,
                    "tokens_used": tokens,
                    "threshold": threshold,
                    "recommendation": f"Use cheaper model for {tokens} tokens",
                    "severity": "low"
                }
        
        return False, {"reason": "model_appropriate"}
    
    def detect_team_anomaly(self, team: str, current_team_cost: float) -> tuple[bool, dict[str, Any]]:
        """
        Detect if a team's spending is unusual compared to history.
        
        Returns: (is_anomaly, details)
        """
        cutoff_time = datetime.now() - timedelta(days=self.baseline_window)
        team_history = [
            d["cost"] for d in self.historical_data
            if d["team"] == team and d["datetime"] >= cutoff_time
        ]
        
        if not team_history or len(team_history) < 5:
            return False, {"reason": "insufficient_history"}
        
        mean_team_cost = statistics.mean(team_history)
        std_team_cost = statistics.stdev(team_history) if len(team_history) > 1 else 0
        
        if std_team_cost == 0:
            return False, {"reason": "no_variance"}
        
        z_score = (current_team_cost - mean_team_cost) / std_team_cost
        
        is_anomaly = z_score > self.spike_threshold
        
        return is_anomaly, {
            "type": "team_anomaly",
            "team": team,
            "current_cost": current_team_cost,
            "historical_mean": mean_team_cost,
            "std_dev": std_team_cost,
            "z_score": z_score,
            "severity": "high" if z_score > 3.0 else "medium"
        }
    
    def analyze_all(self, cost: float, team: str, model: str, tokens: int) -> list[dict[str, Any]]:
        """
        Run all anomaly detection methods and return findings.
        
        Returns: List of detected anomalies
        """
        anomalies = []
        timestamp = datetime.now().isoformat()
        
        # Add this data point
        self.add_data_point(timestamp, cost, team, model, tokens)
        
        # Run detections
        spike_detected, spike_details = self.detect_spike(cost)
        if spike_detected:
            spike_details["model"] = model
            spike_details["team"] = team
            anomalies.append(spike_details)
        
        trend_detected, trend_details = self.detect_trend(team)
        if trend_detected:
            anomalies.append(trend_details)
        
        mismatch_detected, mismatch_details = self.detect_model_mismatch(model, tokens, cost)
        if mismatch_detected:
            anomalies.append(mismatch_details)
        
        team_detected, team_details = self.detect_team_anomaly(team, cost)
        if team_detected:
            anomalies.append(team_details)
        
        return anomalies
    
    def get_summary(self, team: str) -> dict[str, Any]:
        """Get anomaly summary for a team."""
        team_data = [d for d in self.historical_data if d["team"] == team]
        
        if not team_data:
            return {"team": team, "data_points": 0}
        
        costs = [d["cost"] for d in team_data]
        
        return {
            "team": team,
            "data_points": len(team_data),
            "total_cost": sum(costs),
            "avg_cost": statistics.mean(costs),
            "max_cost": max(costs),
            "min_cost": min(costs),
            "std_dev": statistics.stdev(costs) if len(costs) > 1 else 0
        }


# Global anomaly detector instance
detector = AnomalyDetector()


def check_for_anomalies(cost: float, team: str, model: str, tokens: int) -> list[dict[str, Any]]:
    """
    Check for anomalies in a cost event.
    
    Args:
        cost: Cost in dollars
        team: Team name
        model: Model name
        tokens: Total tokens used
    
    Returns:
        List of detected anomalies (empty if none)
    """
    return detector.analyze_all(cost, team, model, tokens)
