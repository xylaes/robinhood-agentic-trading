"""
Automated Portfolio Risk Analysis & Rebalancing Manager Module.
"""
import logging
from src.config import TARGET_ALLOCATION_PCT, DRIFT_TOLERANCE_PCT, SizingEngine

logger = logging.getLogger("portfolio_manager.risk")

class PortfolioRiskAndRebalanceManager:
    """
    Manages Automated Portfolio Risk Analysis & Rebalancing across 3 Asset Buckets:
    1. Equities (~33.3% Target)
    2. Options (~33.3% Target)
    3. Crypto (~33.3% Target)

    Evaluates allocation drift (>10% threshold), cash reserve ratios, concentration risk,
    and scales position sizing dynamically.
    """

    @classmethod
    def analyze_risk_and_rebalance(cls, portfolio_data: dict, positions_data: dict) -> dict:
        logger.info("Evaluating Portfolio Risk Exposure & Automated Rebalancing...")
        p_info = portfolio_data.get("data", {})
        total_val = float(p_info.get("total_value", 0) or p_info.get("equity", 0) or 0)
        cash_val = float(p_info.get("cash", 0) or 0)
        buying_power = float(p_info.get("buying_power", {}).get("buying_power", 0) or 0)

        equity_val = float(p_info.get("equity_value", 0) or 0)
        options_val = float(p_info.get("options_value", 0) or 0)
        crypto_val = float(p_info.get("crypto_value", 0) or 0)

        base_val = total_val if total_val > 0 else 150.0
        current_pcts = {
            "equities": round((equity_val / base_val) * 100, 2),
            "options": round((options_val / base_val) * 100, 2),
            "crypto": round((crypto_val / base_val) * 100, 2),
            "cash": round((cash_val / base_val) * 100, 2)
        }

        # Dynamic dollar targets scaled to current account value
        target_dollars = SizingEngine.get_bucket_targets(base_val)

        # Allocation drifts relative to 33.33% benchmark
        drifts = {
            "equities": round(current_pcts["equities"] - TARGET_ALLOCATION_PCT["equities"], 2),
            "options": round(current_pcts["options"] - TARGET_ALLOCATION_PCT["options"], 2),
            "crypto": round(current_pcts["crypto"] - TARGET_ALLOCATION_PCT["crypto"], 2)
        }

        rebalance_required = any(abs(d) > DRIFT_TOLERANCE_PCT for d in drifts.values())

        # Dynamic order sizes scaled to net worth
        stock_order_size = SizingEngine.get_equity_order_size(base_val, buying_power)
        crypto_order_size = SizingEngine.get_crypto_order_size(base_val, buying_power)
        max_option_premium = SizingEngine.get_max_option_premium(base_val)

        rebalance_actions = []
        if current_pcts["crypto"] < 10.0 and buying_power >= 5.0:
            rebalance_actions.append(f"Deploy cash reserves (${buying_power:.2f} available) to accumulate Crypto dip-buys (${crypto_order_size:.2f} per order) up to ${target_dollars['crypto']:.2f} target.")
        if current_pcts["options"] < 10.0 and buying_power >= 15.0:
            rebalance_actions.append(f"Execute high-delta ITM Call options strategy (max premium cap ${max_option_premium:.2f}) up to ${target_dollars['options']:.2f} target.")
        if current_pcts["equities"] < 20.0 and buying_power >= 5.0:
            rebalance_actions.append(f"Accumulate fractional shares (${stock_order_size:.2f} per order) of NVDA / SPY on 1-hr RSI oversold dips up to ${target_dollars['equities']:.2f} target.")

        if not rebalance_actions:
            rebalance_actions.append("Portfolio is optimally balanced within risk parameters.")

        positions_list = positions_data.get("data", {}).get("positions", [])
        active_positions = [p for p in positions_list if float(p.get("quantity", 0)) > 0]
        concentration_risk = "Low" if len(active_positions) <= 3 else "Moderate"

        return {
            "total_value": total_val,
            "buying_power": buying_power,
            "current_allocations_pct": current_pcts,
            "target_allocation_pct": TARGET_ALLOCATION_PCT,
            "target_dollar_allocations": target_dollars,
            "allocation_drifts_pct": drifts,
            "drift_tolerance_pct": DRIFT_TOLERANCE_PCT,
            "rebalance_required": rebalance_required,
            "rebalance_actions": rebalance_actions,
            "dynamic_scaling_parameters": {
                "scaled_stock_order_size": stock_order_size,
                "scaled_crypto_order_size": crypto_order_size,
                "scaled_max_option_premium": max_option_premium
            },
            "risk_metrics": {
                "concentration_risk": concentration_risk,
                "cash_reserve_ratio_pct": current_pcts["cash"],
                "active_holdings_count": len(active_positions)
            }
        }
