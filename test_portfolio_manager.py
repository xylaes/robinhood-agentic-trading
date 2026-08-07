import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from portfolio_manager import get_target_account

class MockContent:
    def __init__(self, text):
        self.text = text

class MockResponse:
    def __init__(self, content_text):
        self.content = [MockContent(content_text)]

@pytest.mark.asyncio
async def test_get_target_account_from_env():
    # Setup env
    os.environ["ROBINHOOD_ACCOUNT_NUMBER"] = "ENV_ACC_123456"
    try:
        session = AsyncMock()
        res = await get_target_account(session)
        assert res == "ENV_ACC_123456"
        session.call_tool.assert_not_called()
    finally:
        # Cleanup env
        os.environ.pop("ROBINHOOD_ACCOUNT_NUMBER", None)

@pytest.mark.asyncio
async def test_get_target_account_agentic_allowed():
    # Ensure env variable is clear
    if "ROBINHOOD_ACCOUNT_NUMBER" in os.environ:
        del os.environ["ROBINHOOD_ACCOUNT_NUMBER"]

    mock_data = {
        "data": {
            "accounts": [
                {"account_number": "999123456", "agentic_allowed": False},
                {"account_number": "999789012", "agentic_allowed": True},
                {"account_number": "999000000", "agentic_allowed": True}
            ]
        }
    }

    session = AsyncMock()
    session.call_tool.return_value = MockResponse(json.dumps(mock_data))

    res = await get_target_account(session)
    assert res == "999789012"
    session.call_tool.assert_called_once_with("get_accounts", arguments={})

@pytest.mark.asyncio
async def test_get_target_account_fallback():
    # Ensure env variable is clear
    if "ROBINHOOD_ACCOUNT_NUMBER" in os.environ:
        del os.environ["ROBINHOOD_ACCOUNT_NUMBER"]

    mock_data = {
        "data": {
            "accounts": [
                {"account_number": "fallback_primary", "agentic_allowed": False},
                {"account_number": "fallback_secondary", "agentic_allowed": False}
            ]
        }
    }

    session = AsyncMock()
    session.call_tool.return_value = MockResponse(json.dumps(mock_data))

    res = await get_target_account(session)
    assert res == "fallback_primary"
    session.call_tool.assert_called_once_with("get_accounts", arguments={})

@pytest.mark.asyncio
async def test_get_target_account_empty_accounts_error():
    # Ensure env variable is clear
    if "ROBINHOOD_ACCOUNT_NUMBER" in os.environ:
        del os.environ["ROBINHOOD_ACCOUNT_NUMBER"]

    mock_data = {
        "data": {
            "accounts": []
        }
    }

    session = AsyncMock()
    session.call_tool.return_value = MockResponse(json.dumps(mock_data))

    with pytest.raises(RuntimeError) as exc_info:
        await get_target_account(session)

    assert str(exc_info.value) == "No valid Robinhood brokerage accounts found."
    session.call_tool.assert_called_once_with("get_accounts", arguments={})
