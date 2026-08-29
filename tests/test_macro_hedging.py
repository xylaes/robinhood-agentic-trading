"""
Unit tests for EventContractManager in src/macro_hedging.py
"""
from unittest.mock import patch
from src.macro_hedging import EventContractManager


def test_evaluate_macro_hedges_structure():
    """Test standard dictionary structure returned by evaluate_macro_hedges."""
    net_worth = 1000.0
    buying_power = 500.0
    result = EventContractManager.evaluate_macro_hedges(net_worth, buying_power)

    assert isinstance(result, dict)
    assert result["status"] == "active"
    assert result["hedging_enabled"] is True
    assert result["available_buying_power"] == 500.0
    assert "allocated_budget" in result
    assert "catalysts" in result

    catalysts = result["catalysts"]
    assert isinstance(catalysts, list)
    assert len(catalysts) == 3

    for item in catalysts:
        assert "event_name" in item
        assert "ticker" in item
        assert "binary_option" in item
        assert "contract_price_range" in item
        assert "recommended_allocation" in item
        assert "hedge_rationale" in item


def test_evaluate_macro_hedges_budget_min_floor():
    """Test minimum budget floor ($5.00) for low net worth accounts."""
    net_worth = 10.0
    buying_power = 25.0
    result = EventContractManager.evaluate_macro_hedges(net_worth, buying_power)

    assert result["allocated_budget"] == 5.00
    for catalyst in result["catalysts"]:
        assert catalyst["recommended_allocation"] == round(5.00 / 3.0, 2)  # 1.67


def test_evaluate_macro_hedges_budget_proportional():
    """Test proportional budget calculation (10% of net worth) for standard account sizes."""
    net_worth = 200.0
    buying_power = 100.0
    result = EventContractManager.evaluate_macro_hedges(net_worth, buying_power)

    expected_budget = 20.00
    assert result["allocated_budget"] == expected_budget
    for catalyst in result["catalysts"]:
        assert catalyst["recommended_allocation"] == round(expected_budget / 3.0, 2)  # 6.67


def test_evaluate_macro_hedges_budget_max_cap():
    """Test maximum budget cap ($50.00) for high net worth accounts."""
    net_worth = 10000.0
    buying_power = 5000.0
    result = EventContractManager.evaluate_macro_hedges(net_worth, buying_power)

    assert result["allocated_budget"] == 50.00
    for catalyst in result["catalysts"]:
        assert catalyst["recommended_allocation"] == round(50.00 / 3.0, 2)  # 16.67


def test_evaluate_macro_hedges_catalysts_content():
    """Test specific macro catalysts details (FOMC, CPI, NFP)."""
    result = EventContractManager.evaluate_macro_hedges(1000.0, 500.0)
    catalysts = result["catalysts"]

    fomc = catalysts[0]
    assert fomc["event_name"] == "FOMC Interest Rate Decision"
    assert fomc["ticker"] == "FED-RATE-CUT"
    assert fomc["binary_option"] == "YES"

    cpi = catalysts[1]
    assert cpi["event_name"] == "US CPI YoY Inflation Release"
    assert cpi["ticker"] == "CPI-YOY-UNDER-2.8"
    assert cpi["binary_option"] == "YES"

    nfp = catalysts[2]
    assert nfp["event_name"] == "Non-Farm Payrolls (NFP) Employment"
    assert nfp["ticker"] == "NFP-OVER-150K"
    assert nfp["binary_option"] == "YES"


def test_evaluate_macro_hedges_with_mocked_sizing_engine():
    """Test evaluate_macro_hedges when SizingEngine returns a mocked budget."""
    with patch("src.macro_hedging.SizingEngine.get_macro_hedge_budget", return_value=30.00) as mock_budget:
        result = EventContractManager.evaluate_macro_hedges(net_worth=500.0, buying_power=100.0)
        mock_budget.assert_called_once_with(500.0)
        assert result["allocated_budget"] == 30.00
        assert result["available_buying_power"] == 100.0
        for catalyst in result["catalysts"]:
            assert catalyst["recommended_allocation"] == 10.00
