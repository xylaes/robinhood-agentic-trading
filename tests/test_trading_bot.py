import json
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock
from trading_bot import TradingBot


@pytest.mark.asyncio
async def test_buy_position_simulation_logging_no_sensitive_data(caplog):
    bot = TradingBot(account_number="12345678", dry_run=True)

    mock_session = AsyncMock()
    mock_res = MagicMock()
    sensitive_payload = {"account_number": "12345678", "sensitive_broker_metric": "secret_data_value"}
    mock_res.content = [MagicMock(text=json.dumps(sensitive_payload))]
    mock_session.call_tool.return_value = mock_res

    with caplog.at_level(logging.INFO):
        await bot.buy_position(mock_session, "AAPL", 10.0, 150.0, is_settled=True)

    mock_session.call_tool.assert_called_with("review_equity_order", arguments={
        "account_number": "12345678",
        "symbol": "AAPL",
        "side": "buy",
        "type": "market",
        "dollar_amount": "10.00"
    })

    logs = caplog.text
    assert "Pre-trade simulation review completed successfully." in logs
    assert "secret_data_value" not in logs
    assert "sensitive_broker_metric" not in logs


@pytest.mark.asyncio
async def test_sell_position_simulation_logging_no_sensitive_data(caplog):
    bot = TradingBot(account_number="12345678", dry_run=True)

    mock_session = AsyncMock()
    mock_res = MagicMock()
    sensitive_payload = {"account_number": "12345678", "sensitive_broker_metric": "secret_data_value"}
    mock_res.content = [MagicMock(text=json.dumps(sensitive_payload))]
    mock_session.call_tool.return_value = mock_res

    with caplog.at_level(logging.INFO):
        await bot.sell_position(mock_session, "AAPL", 1.0, 150.0, "take_profit", 140.0)

    mock_session.call_tool.assert_called_with("review_equity_order", arguments={
        "account_number": "12345678",
        "symbol": "AAPL",
        "side": "sell",
        "type": "market",
        "quantity": "1.000000"
    })

    logs = caplog.text
    assert "Pre-trade simulation review completed successfully." in logs
    assert "secret_data_value" not in logs
    assert "sensitive_broker_metric" not in logs
