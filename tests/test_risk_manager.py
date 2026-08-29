import pytest
from src.risk_manager import PortfolioRiskAndRebalanceManager


def test_analyze_risk_and_rebalance_balanced():
    """Test portfolio that is optimally balanced within drift tolerance."""
    portfolio_data = {
        "data": {
            "total_value": 1000.0,
            "cash": 100.0,
            "equity_value": 333.3,
            "options_value": 333.3,
            "crypto_value": 333.3,
            "buying_power": {"buying_power": 100.0}
        }
    }
    positions_data = {
        "data": {
            "positions": [
                {"symbol": "NVDA", "quantity": "10"},
                {"symbol": "BTC", "quantity": "0.5"}
            ]
        }
    }

    result = PortfolioRiskAndRebalanceManager.analyze_risk_and_rebalance(portfolio_data, positions_data)

    assert result["total_value"] == 1000.0
    assert result["buying_power"] == 100.0
    assert result["current_allocations_pct"]["equities"] == 33.33
    assert result["current_allocations_pct"]["options"] == 33.33
    assert result["current_allocations_pct"]["crypto"] == 33.33
    assert result["current_allocations_pct"]["cash"] == 10.0

    assert result["rebalance_required"] is False
    assert result["rebalance_actions"] == ["Portfolio is optimally balanced within risk parameters."]
    assert result["risk_metrics"]["concentration_risk"] == "Low"
    assert result["risk_metrics"]["active_holdings_count"] == 2


def test_analyze_risk_and_rebalance_unbalanced_underweight():
    """Test portfolio with underweight buckets requiring rebalance actions."""
    portfolio_data = {
        "data": {
            "total_value": 1000.0,
            "cash": 800.0,
            "equity_value": 100.0,   # 10.0% (< 20.0%)
            "options_value": 50.0,    # 5.0% (< 10.0%)
            "crypto_value": 50.0,     # 5.0% (< 10.0%)
            "buying_power": {"buying_power": 100.0}
        }
    }
    positions_data = {
        "data": {
            "positions": [
                {"symbol": "NVDA", "quantity": "1"},
                {"symbol": "AAPL", "quantity": "1"},
                {"symbol": "SPY", "quantity": "1"},
                {"symbol": "QQQ", "quantity": "1"}
            ]
        }
    }

    result = PortfolioRiskAndRebalanceManager.analyze_risk_and_rebalance(portfolio_data, positions_data)

    assert result["rebalance_required"] is True
    assert len(result["rebalance_actions"]) == 3
    assert "accumulate Crypto dip-buys" in result["rebalance_actions"][0]
    assert "Execute high-delta ITM Call options strategy" in result["rebalance_actions"][1]
    assert "Accumulate fractional shares" in result["rebalance_actions"][2]

    assert result["risk_metrics"]["concentration_risk"] == "Moderate"
    assert result["risk_metrics"]["active_holdings_count"] == 4


def test_analyze_risk_and_rebalance_unbalanced_overweight_no_buying_power():
    """Test overweight portfolio with zero buying power."""
    portfolio_data = {
        "data": {
            "total_value": 1000.0,
            "cash": 0.0,
            "equity_value": 600.0,   # 60.0% (drift +26.67%)
            "options_value": 200.0,   # 20.0%
            "crypto_value": 200.0,    # 20.0%
            "buying_power": {"buying_power": 0.0}
        }
    }
    positions_data = {"data": {"positions": []}}

    result = PortfolioRiskAndRebalanceManager.analyze_risk_and_rebalance(portfolio_data, positions_data)

    assert result["rebalance_required"] is True
    # Buying power is 0, so conditional rebalance actions are skipped, falling back to default message
    assert result["rebalance_actions"] == ["Portfolio is optimally balanced within risk parameters."]
    assert result["risk_metrics"]["concentration_risk"] == "Low"
    assert result["risk_metrics"]["active_holdings_count"] == 0


def test_analyze_risk_and_rebalance_fallback_values():
    """Test fallback logic when total_value is 0 or missing and equity is present, or when net worth <= 0."""
    # Case 1: total_value is 0, fallback to equity
    p1 = {
        "data": {
            "equity": 500.0,
            "cash": 50.0,
            "equity_value": 150.0,
            "buying_power": {"buying_power": 25.0}
        }
    }
    r1 = PortfolioRiskAndRebalanceManager.analyze_risk_and_rebalance(p1, {})
    assert r1["total_value"] == 500.0

    # Case 2: total_value and equity both 0/missing -> base_val falls back to 150.0
    p2 = {"data": {}}
    r2 = PortfolioRiskAndRebalanceManager.analyze_risk_and_rebalance(p2, {})
    assert r2["total_value"] == 0.0
    assert r2["current_allocations_pct"]["equities"] == 0.0
    assert r2["target_dollar_allocations"]["equities"] == round(150.0 * 0.3333, 2)


def test_analyze_risk_and_rebalance_positions_filtering():
    """Test filtering out zero or negative quantity positions."""
    portfolio_data = {"data": {"total_value": 300.0}}
    positions_data = {
        "data": {
            "positions": [
                {"symbol": "NVDA", "quantity": "5"},
                {"symbol": "AAPL", "quantity": "0"},
                {"symbol": "TSLA", "quantity": "-1"},
                {"symbol": "BTC", "quantity": "0.1"}
            ]
        }
    }

    result = PortfolioRiskAndRebalanceManager.analyze_risk_and_rebalance(portfolio_data, positions_data)

    assert result["risk_metrics"]["active_holdings_count"] == 2
    assert result["risk_metrics"]["concentration_risk"] == "Low"
