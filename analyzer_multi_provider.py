"""
Multi-Provider LLM Analyzer
Enhanced wrapper for cost_analyzer with additional multi-provider features.
"""

import logging
from typing import Any

import pandas as pd

from cost_analyzer import CostAnalyzer

logger = logging.getLogger(__name__)


class MultiProviderAnalyzer:
    """
    Enhanced analyzer with multi-provider comparison and optimization features.
    Wraps CostAnalyzer to provide higher-level functionality.
    """

    def __init__(self):
        self.base_analyzer = CostAnalyzer()
        self.provider_stats = {}

    def get_all_provider_pricing(self) -> dict[str, Any]:
        """Get current pricing for all supported AI providers"""
        pricing_info = {}

        # Extract from base analyzer's pricing
        providers = {}

        for model_name, pricing in self.base_analyzer.pricing.items():
            provider = pricing.provider.value
            if provider not in providers:
                providers[provider] = {
                    "models": [],
                    "min_input": float('inf'),
                    "max_output": 0
                }

            input_price = float(pricing.input_price)
            output_price = float(pricing.output_price)

            providers[provider]["models"].append({
                "name": model_name,
                "input_price_per_1k_tokens": input_price,
                "output_price_per_1k_tokens": output_price
            })

            providers[provider]["min_input"] = min(
                providers[provider]["min_input"], 
                input_price
            )
            providers[provider]["max_output"] = max(
                providers[provider]["max_output"], 
                output_price
            )

        # Format output
        for provider, data in providers.items():
            pricing_info[provider] = {
                "model_count": len(data["models"]),
                "models": data["models"],
                "price_range": {
                    "input_min": round(data["min_input"], 6),
                    "output_max": round(data["max_output"], 6)
                }
            }

        return pricing_info

    def compare_providers(self, usage_data: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Compare costs across providers for given usage patterns.
        
        Args:
            usage_data: List of usage records with model and token counts
            
        Returns:
            Comparison showing cost by provider
        """
        if not usage_data:
            return {"error": "No usage data provided"}

        comparison = {
            "by_provider": {},
            "recommendations": [],
            "total_cost": 0,
            "savings_opportunity": 0
        }

        # Calculate costs by provider
        for record in usage_data:
            model = record.get("model", "unknown")
            prompt_tokens = record.get("prompt_tokens", 0)
            completion_tokens = record.get("completion_tokens", 0)

            # Get pricing
            pricing, is_known = self.base_analyzer._get_model_pricing(model)
            if not is_known:
                continue

            cost = self.base_analyzer._calculate_row_cost(
                prompt_tokens,
                completion_tokens,
                pricing
            )

            provider = self.base_analyzer._detect_provider(model)
            provider_name = provider.value

            if provider_name not in comparison["by_provider"]:
                comparison["by_provider"][provider_name] = {
                    "cost": 0,
                    "requests": 0,
                    "models_used": set()
                }

            comparison["by_provider"][provider_name]["cost"] += float(cost)
            comparison["by_provider"][provider_name]["requests"] += 1
            comparison["by_provider"][provider_name]["models_used"].add(model)

            comparison["total_cost"] += float(cost)

        # Convert sets to lists for JSON serialization
        for provider_data in comparison["by_provider"].values():
            provider_data["models_used"] = list(provider_data["models_used"])

        # Generate recommendations
        if comparison["by_provider"]:
            cheapest_provider = min(
                comparison["by_provider"].items(),
                key=lambda x: x[1]["cost"]
            )

            for provider_name, data in comparison["by_provider"].items():
                if provider_name != cheapest_provider[0]:
                    savings = data["cost"] - (
                        data["cost"] * (cheapest_provider[1]["cost"] / (data["cost"] + 0.01))
                    )
                    if savings > 0:
                        comparison["recommendations"].append({
                            "current_provider": provider_name,
                            "recommended_provider": cheapest_provider[0],
                            "potential_savings": round(savings, 2),
                            "requests_affected": data["requests"]
                        })

        return comparison

    def analyze_with_optimization(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Analyze usage and provide optimization recommendations across providers.
        
        Args:
            df: DataFrame with usage data
            
        Returns:
            Analysis results with multi-provider optimizations
        """
        # Get base analysis
        results = self.base_analyzer.analyze_usage(df)

        # Add provider optimization layer
        if "provider_breakdown" in results:
            provider_breakdown = results["provider_breakdown"]

            # Identify most expensive provider
            most_expensive = max(
                provider_breakdown.items(),
                key=lambda x: x[1].get("cost", 0)
            )

            results["optimization"] = {
                "most_expensive_provider": most_expensive[0],
                "cost": most_expensive[1].get("cost", 0),
                "models_affected": most_expensive[1].get("models", [])[:5],  # Top 5
                "recommendation": f"Review {most_expensive[0]} usage for cost optimization"
            }

        return results

    def get_provider_breakdown_detailed(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Get detailed breakdown by provider with team information.
        
        Args:
            df: DataFrame with usage data
            
        Returns:
            Detailed provider and team breakdown
        """
        results = self.base_analyzer.analyze_usage(df)

        breakdown = {
            "total_cost": results.get("total_cost", 0),
            "provider_team_breakdown": {}
        }

        # Build provider-team matrix
        if "provider_breakdown" in results:
            for provider_name, provider_data in results["provider_breakdown"].items():
                breakdown["provider_team_breakdown"][provider_name] = {
                    "cost": provider_data.get("cost", 0),
                    "percentage": (
                        provider_data.get("cost", 0) / results.get("total_cost", 1) * 100
                    ),
                    "models": provider_data.get("models", [])
                }

        return breakdown

    def estimate_cost_migration(
        self,
        current_provider: str,
        target_provider: str,
        usage_data: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Estimate cost savings from migrating to a different provider.
        
        Args:
            current_provider: Current provider name
            target_provider: Target provider name
            usage_data: List of usage records
            
        Returns:
            Migration cost estimate and savings
        """
        current_cost = 0
        target_cost = 0

        for record in usage_data:
            model = record.get("model", "unknown")
            prompt_tokens = record.get("prompt_tokens", 0)
            completion_tokens = record.get("completion_tokens", 0)

            # Get current cost
            pricing, is_known = self.base_analyzer._get_model_pricing(model)
            if is_known:
                current_cost += float(
                    self.base_analyzer._calculate_row_cost(
                        prompt_tokens,
                        completion_tokens,
                        pricing
                    )
                )

            # Estimate target cost (use target provider's cheapest equivalent model)
            # For simplicity, apply a fixed provider multiplier
            provider_multipliers = {
                "openai": 1.0,
                "anthropic": 1.1,
                "google": 0.9,
                "azure": 0.85
            }

            target_multiplier = provider_multipliers.get(target_provider, 1.0)
            target_cost = current_cost * target_multiplier

        savings = current_cost - target_cost
        savings_percent = (savings / current_cost * 100) if current_cost > 0 else 0

        return {
            "current_provider": current_provider,
            "target_provider": target_provider,
            "current_monthly_cost": round(current_cost, 2),
            "estimated_target_cost": round(target_cost, 2),
            "estimated_savings": round(savings, 2),
            "savings_percentage": round(savings_percent, 1),
            "payback_recommendation": (
                "Recommended" if savings_percent > 10 else "Not recommended"
            )
        }
