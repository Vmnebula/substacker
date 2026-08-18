"""
Budget Enforcement System
Manages budget limits and enforcement actions for AI cost control.
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class BudgetAction(Enum):
    """Actions to take when budget is exceeded"""
    ALERT = "alert"  # Send alert but allow usage
    THROTTLE = "throttle"  # Reduce rate limits
    BLOCK = "block"  # Block API calls
    GRADUAL_REDUCE = "gradual_reduce"  # Gradually reduce quota


class BudgetType(Enum):
    """Types of budget limits"""
    MONTHLY = "monthly"
    DAILY = "daily"
    HOURLY = "hourly"
    PROJECT = "project"


class BudgetEnforcer:
    """
    Enforces budget limits and takes actions when limits are exceeded.
    """

    def __init__(self, db):
        self.db = db
        self.budgets = {}  # In-memory cache of user budgets
        self.usage_cache = {}  # Track current period usage
        self.load_budgets()

    def load_budgets(self):
        """Load budgets from database"""
        try:
            # Query budgets table (assuming it exists in database)
            # This is a placeholder - implement based on actual schema
            logger.info("Budgets loaded from database")
        except Exception as e:
            logger.error(f"Failed to load budgets: {e}")

    def set_budget(
        self,
        user_email: str,
        budget_type: str,
        amount: float,
        team: str | None = None
    ) -> bool:
        """
        Set budget limit for a user or team.

        Args:
            user_email: User email
            budget_type: "monthly", "daily", "hourly", or "project"
            amount: Budget amount in dollars
            team: Optional team name

        Returns:
            Success status
        """
        try:
            key = f"{user_email}:{budget_type}:{team or 'all'}"

            self.budgets[key] = {
                "user_email": user_email,
                "type": budget_type,
                "amount": amount,
                "team": team,
                "created_at": datetime.now().isoformat(),
                "active": True
            }

            # Persist to database
            self._save_budget_to_db(key, self.budgets[key])

            logger.info(f"Budget set for {user_email}: {budget_type} ${amount}")
            return True

        except Exception as e:
            logger.error(f"Failed to set budget: {e}")
            return False

    def get_user_budgets(self, user_email: str) -> list[dict[str, Any]]:
        """Get all budget settings for a user"""
        return [
            budget for budget in self.budgets.values()
            if budget["user_email"] == user_email
        ]

    def get_budget_status(self, user_email: str) -> dict[str, Any]:
        """
        Get current budget status and usage.

        Args:
            user_email: User email

        Returns:
            Budget status with current usage and remaining budget
        """
        status = {
            "user_email": user_email,
            "budgets": {},
            "overall_status": "healthy",
            "alerts": []
        }

        user_budgets = self.get_user_budgets(user_email)

        for budget in user_budgets:
            budget_key = f"{user_email}:{budget['type']}:{budget['team'] or 'all'}"
            current_usage = self._get_current_usage(user_email, budget["type"], budget.get("team"))

            remaining = budget["amount"] - current_usage
            usage_percent = (current_usage / budget["amount"] * 100) if budget["amount"] > 0 else 0

            budget_status = {
                "type": budget["type"],
                "team": budget.get("team", "all"),
                "limit": budget["amount"],
                "used": round(current_usage, 2),
                "remaining": round(remaining, 2),
                "usage_percent": round(usage_percent, 1),
                "status": self._get_budget_status_label(usage_percent)
            }

            status["budgets"][budget_key] = budget_status

            # Check for alerts
            if usage_percent > 90:
                status["overall_status"] = "warning"
                status["alerts"].append({
                    "type": "high_usage",
                    "budget_type": budget["type"],
                    "team": budget.get("team", "all"),
                    "usage_percent": usage_percent,
                    "message": f"Budget usage at {usage_percent:.1f}%"
                })

            if usage_percent >= 100:
                status["overall_status"] = "critical"
                status["alerts"].append({
                    "type": "budget_exceeded",
                    "budget_type": budget["type"],
                    "team": budget.get("team", "all"),
                    "message": f"Budget exceeded by ${abs(remaining):.2f}"
                })

        return status

    def check_budget_limit(self, user_email: str, proposed_cost: float) -> dict[str, Any]:
        """
        Check if a proposed usage would exceed budget.

        Args:
            user_email: User email
            proposed_cost: Cost of proposed operation

        Returns:
            Permission and action details
        """
        status = self.get_budget_status(user_email)

        if status["overall_status"] == "critical":
            return {
                "allowed": False,
                "reason": "Budget exceeded",
                "action": "block",
                "message": "Monthly budget exceeded. Usage blocked."
            }

        if status["overall_status"] == "warning":
            return {
                "allowed": True,
                "reason": "Budget warning",
                "action": "alert",
                "message": f"Warning: Budget {status['alerts'][0]['usage_percent']:.1f}% used"
            }

        return {
            "allowed": True,
            "reason": "Within budget",
            "action": "allow",
            "message": "Usage allowed"
        }

    def _get_current_usage(
        self,
        user_email: str,
        budget_type: str,
        team: str | None = None
    ) -> float:
        """Get current usage for a budget period"""
        try:
            now = datetime.now()

            if budget_type == "monthly":
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            elif budget_type == "daily":
                period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif budget_type == "hourly":
                period_start = now.replace(minute=0, second=0, microsecond=0)
            else:
                return 0

            # Query usage logs for this period
            usage_logs = self.db.get_usage_logs(user_email, period_start, now, team)
            total_cost = sum(log.get("cost", 0) for log in usage_logs)

            return total_cost

        except Exception as e:
            logger.error(f"Failed to get current usage: {e}")
            return 0

    def _get_budget_status_label(self, usage_percent: float) -> str:
        """Get human-readable budget status"""
        if usage_percent >= 100:
            return "exceeded"
        elif usage_percent >= 90:
            return "critical"
        elif usage_percent >= 75:
            return "warning"
        else:
            return "healthy"

    def _save_budget_to_db(self, key: str, budget: dict[str, Any]):
        """Save budget to database"""
        try:
            # Placeholder - implement based on actual database schema
            # self.db.save_budget(budget)
            pass
        except Exception as e:
            logger.error(f"Failed to save budget to database: {e}")

    def enforce_budget(
        self,
        user_email: str,
        cost: float,
        team: str | None = None
    ) -> dict[str, Any]:
        """
        Enforce budget limits and return action to take.

        Args:
            user_email: User email
            cost: Cost of this operation
            team: Optional team name

        Returns:
            Enforcement action and details
        """
        permission = self.check_budget_limit(user_email, cost)

        if not permission["allowed"]:
            logger.warning(f"Budget enforcement blocked request for {user_email}")
            return {
                "action": BudgetAction.BLOCK.value,
                "reason": permission["reason"],
                "allowed": False
            }

        status = self.get_budget_status(user_email)
        if status["overall_status"] == "warning":
            return {
                "action": BudgetAction.ALERT.value,
                "reason": "Approaching budget limit",
                "allowed": True,
                "usage_percent": status["budgets"][list(status["budgets"].keys())[0]]["usage_percent"]
            }

        return {
            "action": BudgetAction.ALERT.value,
            "reason": "Within budget",
            "allowed": True
        }

    def get_budget_forecast(self, user_email: str, days_ahead: int = 30) -> dict[str, Any]:
        """
        Forecast budget usage for the next N days.

        Args:
            user_email: User email
            days_ahead: Number of days to forecast

        Returns:
            Forecast with trend and recommendations
        """
        try:
            # Get last 30 days of usage
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

            usage_logs = self.db.get_usage_logs(user_email, start_date, end_date)

            if not usage_logs:
                return {"error": "Insufficient historical data"}

            # Calculate daily average
            daily_costs = {}
            for log in usage_logs:
                date = log["timestamp"][:10]
                daily_costs[date] = daily_costs.get(date, 0) + log.get("cost", 0)

            avg_daily_cost = sum(daily_costs.values()) / len(daily_costs) if daily_costs else 0

            # Project to monthly
            projected_monthly_cost = avg_daily_cost * 30

            user_budgets = self.get_user_budgets(user_email)
            monthly_budget = next(
                (b["amount"] for b in user_budgets if b["type"] == "monthly"),
                None
            )

            forecast = {
                "projection_period_days": days_ahead,
                "average_daily_cost": round(avg_daily_cost, 2),
                "projected_monthly_cost": round(projected_monthly_cost, 2),
                "monthly_budget": monthly_budget,
                "trend": "increasing" if projected_monthly_cost > (monthly_budget or 0) else "healthy",
                "recommendation": (
                    "Budget exceeded by end of month. Consider cost optimization."
                    if monthly_budget and projected_monthly_cost > monthly_budget
                    else "Budget tracking normal"
                )
            }

            return forecast

        except Exception as e:
            logger.error(f"Failed to forecast budget: {e}")
            return {"error": str(e)}
