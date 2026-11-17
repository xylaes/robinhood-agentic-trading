"""
Centralized Configuration & Dynamic Capital Sizing Engine for Robinhood Agentic Trading.
"""

# Capital Thresholds & Benchmarks
OPTIONS_MIN_NET_WORTH_THRESHOLD = 500.00  # Minimum capital to trade non-fractional 100-share options

# Account Target Allocation Benchmarks (%)
# Tailored for small accounts: 60% Equities / 40% Crypto with 0% Options (<$500)
TARGET_ALLOCATION_PCT = {
    "equities": 60.00,
    "crypto": 40.00,
    "options": 0.00
}

# Risk Boundaries & Tolerances
DRIFT_TOLERANCE_PCT = 10.0  # Alert & trigger rebalancing if bucket strays > 10%

# Strategy Watchlists (Expanded for Active Dynamic Opportunities)
EQUITY_WATCHLIST = ["NVDA", "TSLA", "AMD", "PLTR", "SPY", "QQQ", "AAPL", "COIN", "MSFT", "AMZN"]
CRYPTO_WATCHLIST = ["BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD", "AVAX-USD"]

# Robinhood Crypto & Banking API / MCP Endpoint Configs
ROBINHOOD_CRYPTO_BASE_URL = "https://trading.robinhood.com"
ROBINHOOD_BANKING_MCP_URL = "https://banking-agent.robinhood.com/mcp/banking"



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
        Options bucket remains dormant ($0) until net worth reaches OPTIONS_MIN_NET_WORTH_THRESHOLD ($500).
        """
        base_val = net_worth if net_worth > 0 else 150.0
        if base_val >= OPTIONS_MIN_NET_WORTH_THRESHOLD:
            return {
                "equities": round(base_val * 0.40, 2),
                "crypto": round(base_val * 0.30, 2),
                "options": round(base_val * 0.30, 2)
            }
        return {
            "equities": round(base_val * (TARGET_ALLOCATION_PCT["equities"] / 100.0), 2),
            "crypto": round(base_val * (TARGET_ALLOCATION_PCT["crypto"] / 100.0), 2),
            "options": 0.00
        }

    @staticmethod
    def get_equity_order_size(net_worth: float, buying_power: float) -> float:
        """
        Calculates dynamic fractional stock order size (10% of equity bucket target).
        """
        targets = SizingEngine.get_bucket_targets(net_worth)
        bucket_target = targets.get("equities", net_worth * 0.60)
        calculated_size = round(bucket_target * 0.10, 2)
        return max(5.00, min(calculated_size, buying_power if buying_power >= 5.0 else 5.00))

    @staticmethod
    def get_crypto_order_size(net_worth: float, buying_power: float) -> float:
        """
        Calculates dynamic fractional crypto order size (10% of crypto bucket target).
        """
        targets = SizingEngine.get_bucket_targets(net_worth)
        bucket_target = targets.get("crypto", net_worth * 0.40)
        calculated_size = round(bucket_target * 0.10, 2)
        return max(5.00, min(calculated_size, buying_power if buying_power >= 5.0 else 5.00))

    @staticmethod
    def get_max_option_premium(net_worth: float) -> float:
        """
        Calculates dynamic max option contract premium cap.
        Dormant ($0.00) while net worth is under $500 threshold.
        """
        if net_worth < OPTIONS_MIN_NET_WORTH_THRESHOLD:
            return 0.00
        bucket_target = net_worth * 0.30
        return max(25.00, round(bucket_target * 0.50, 2))

    @staticmethod
    def get_macro_hedge_budget(net_worth: float) -> float:
        """
        Calculates dynamic macro catalyst event contract hedging budget.
        """
        return max(5.00, min(round(net_worth * 0.10, 2), 50.00))
