"""
Centralized Configuration & Dynamic Capital Sizing Engine for Robinhood Agentic Trading.
"""

# Account Target Allocation Benchmarks (%)
TARGET_ALLOCATION_PCT = {
    "equities": 33.33,
    "options": 33.33,
    "crypto": 33.33
}

# Risk Boundaries & Tolerances
DRIFT_TOLERANCE_PCT = 10.0  # Alert & trigger rebalancing if bucket strays > 10%

# Strategy Watchlists
EQUITY_WATCHLIST = ["NVDA", "SPY", "QQQ", "AAPL"]
CRYPTO_WATCHLIST = ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD"]

# Robinhood Crypto API Endpoint Config
ROBINHOOD_CRYPTO_BASE_URL = "https://trading.robinhood.com"


# Dynamic Capital Scaling Functions
class SizingEngine:
    """
    Scales position sizing, risk caps, and order limits dynamically
    based on live account net worth ($150 -> $1,000 -> $10,000+).
    """

    @staticmethod
    def get_bucket_targets(net_worth: float) -> dict:
        """
        Calculates target dollar allocations for each bucket based on net worth.
        """
        base_val = net_worth if net_worth > 0 else 150.0
        return {
            "equities": round(base_val * 0.3333, 2),
            "options": round(base_val * 0.3333, 2),
            "crypto": round(base_val * 0.3333, 2)
        }

    @staticmethod
    def get_equity_order_size(net_worth: float, buying_power: float) -> float:
        """
        Calculates dynamic fractional stock order size (20% of equity bucket target).
        """
        bucket_target = net_worth * 0.3333
        calculated_size = round(bucket_target * 0.20, 2)
        return max(5.00, min(calculated_size, buying_power))

    @staticmethod
    def get_crypto_order_size(net_worth: float, buying_power: float) -> float:
        """
        Calculates dynamic fractional crypto order size (20% of crypto bucket target).
        """
        bucket_target = net_worth * 0.3333
        calculated_size = round(bucket_target * 0.20, 2)
        return max(5.00, min(calculated_size, buying_power))

    @staticmethod
    def get_max_option_premium(net_worth: float) -> float:
        """
        Calculates dynamic max option contract premium cap (70% of option bucket target).
        """
        bucket_target = net_worth * 0.3333
        return max(15.00, round(bucket_target * 0.70, 2))

    @staticmethod
    def get_macro_hedge_budget(net_worth: float) -> float:
        """
        Calculates dynamic macro catalyst event contract hedging budget.
        """
        return max(5.00, min(round(net_worth * 0.10, 2), 50.00))
