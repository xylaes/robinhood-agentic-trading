import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from portfolio_manager import run_portfolio_cycle, get_target_account


@pytest.fixture
def mock_mcp_session():
    session = AsyncMock()

    async def call_tool_side_effect(name, arguments=None):
        mock_response = MagicMock()
        if name == "get_accounts":
            mock_response.content = [MagicMock(text=json.dumps({
                "data": {"accounts": [{"account_number": "12345678", "agentic_allowed": True}]}
            }))]
        elif name == "get_portfolio":
            mock_response.content = [MagicMock(text=json.dumps({
                "data": {"equity": "1000.00", "buying_power": {"buying_power": "500.00"}}
            }))]
        elif name == "get_equity_positions":
            mock_response.content = [MagicMock(text=json.dumps({
                "data": []
            }))]
        elif name == "get_equity_quotes":
            mock_response.content = [MagicMock(text=json.dumps({
                "data": {}
            }))]
        elif name == "get_equity_technical_indicators":
            mock_response.content = [MagicMock(text=json.dumps({
                "data": {}
            }))]
        elif name in ["review_equity_order", "review_option_order"]:
            mock_response.content = [MagicMock(text=json.dumps({
                "status": "simulated"
            }))]
        elif name == "search":
            mock_response.content = [MagicMock(text=json.dumps({
                "result": "crypto_search"
            }))]
        else:
            mock_response.content = [MagicMock(text=json.dumps({}))]
        return mock_response

    session.call_tool.side_effect = call_tool_side_effect
    return session


@pytest.mark.asyncio
async def test_get_target_account_from_env():
    with patch("os.getenv", return_value="12349999"):
        session = AsyncMock()
        acc = await get_target_account(session)
        assert acc == "12349999"
        session.call_tool.assert_not_called()


@pytest.mark.asyncio
async def test_get_target_account_from_mcp_agentic(mock_mcp_session):
    with patch("os.getenv", return_value=""):
        acc = await get_target_account(mock_mcp_session)
        assert acc == "12345678"


@pytest.mark.asyncio
async def test_run_portfolio_cycle_full(mock_mcp_session):
    # Setup async context managers for stdio_client and ClientSession
    mock_stdio = AsyncMock()
    mock_stdio.__aenter__.return_value = (MagicMock(), MagicMock())

    mock_client_session_cm = AsyncMock()
    mock_client_session_cm.__aenter__.return_value = mock_mcp_session

    with patch("portfolio_manager.stdio_client", return_value=mock_stdio), \
         patch("portfolio_manager.ClientSession", return_value=mock_client_session_cm), \
         patch("portfolio_manager.GitHubSourceOfTruth.verify_alignment", return_value={"aligned": True}), \
         patch("portfolio_manager.RobinhoodCryptoClient") as mock_crypto_cls, \
         patch("portfolio_manager.EventContractManager.evaluate_macro_hedges", return_value={"hedges": []}), \
         patch("portfolio_manager.PortfolioRiskAndRebalanceManager.analyze_risk_and_rebalance", return_value={"risk": "ok"}), \
         patch("portfolio_manager.PortfolioDigestGenerator.generate_digest") as mock_digest, \
         patch("builtins.open", mock_open()):

        mock_crypto_inst = mock_crypto_cls.return_value
        mock_crypto_inst.get_best_bid_ask.return_value = {"results": [{"symbol": "BTC-USD", "price": "50000"}]}
        mock_crypto_inst.get_account.return_value = {"account": "crypto123"}
        mock_crypto_inst.place_order.return_value = {"simulated": True}

        res = await run_portfolio_cycle(target_branch="full")

        assert res["target_branch"] == "full"
        assert res["account_number"] == "12345678"
        assert "portfolio" in res
        assert "positions" in res
        assert "quotes" in res
        assert "indicators" in res
        assert "crypto_quotes" in res
        assert "crypto_account" in res
        assert "event_contracts" in res
        assert "simulations" in res
        assert "risk_and_rebalance" in res
        mock_digest.assert_called_once()


@pytest.mark.asyncio
async def test_run_portfolio_cycle_branches(mock_mcp_session):
    mock_stdio = AsyncMock()
    mock_stdio.__aenter__.return_value = (MagicMock(), MagicMock())

    mock_client_session_cm = AsyncMock()
    mock_client_session_cm.__aenter__.return_value = mock_mcp_session

    for branch in ["equities", "crypto", "events", "options"]:
        with patch("portfolio_manager.stdio_client", return_value=mock_stdio), \
             patch("portfolio_manager.ClientSession", return_value=mock_client_session_cm), \
             patch("portfolio_manager.GitHubSourceOfTruth.verify_alignment", return_value={"aligned": True}), \
             patch("portfolio_manager.RobinhoodCryptoClient") as mock_crypto_cls, \
             patch("portfolio_manager.EventContractManager.evaluate_macro_hedges", return_value={"hedges": []}), \
             patch("portfolio_manager.PortfolioRiskAndRebalanceManager.analyze_risk_and_rebalance", return_value={"risk": "ok"}), \
             patch("portfolio_manager.PortfolioDigestGenerator.generate_digest"), \
             patch("builtins.open", mock_open()):

            mock_crypto_inst = mock_crypto_cls.return_value
            mock_crypto_inst.get_best_bid_ask.return_value = None
            mock_crypto_inst.get_account.return_value = {}
            mock_crypto_inst.place_order.return_value = {}

            res = await run_portfolio_cycle(target_branch=branch)
            assert res["target_branch"] == branch


@pytest.mark.asyncio
async def test_run_portfolio_cycle_error():
    mock_stdio = AsyncMock()
    mock_stdio.__aenter__.side_effect = Exception("Connection failed")

    with patch("portfolio_manager.stdio_client", return_value=mock_stdio), \
         patch("portfolio_manager.GitHubSourceOfTruth.verify_alignment", return_value={"aligned": True}):

        with pytest.raises(Exception, match="Connection failed"):
            await run_portfolio_cycle(target_branch="full")
