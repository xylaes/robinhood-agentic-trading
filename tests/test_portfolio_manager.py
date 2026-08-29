import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from portfolio_manager import get_target_account

@pytest.mark.asyncio
async def test_get_target_account_env_valid(monkeypatch):
    monkeypatch.setenv("ROBINHOOD_ACCOUNT_NUMBER", "5UB12345678")
    session = AsyncMock()
    account = await get_target_account(session)
    assert account == "5UB12345678"
    session.call_tool.assert_not_called()

@pytest.mark.asyncio
async def test_get_target_account_env_placeholder_your(monkeypatch):
    monkeypatch.setenv("ROBINHOOD_ACCOUNT_NUMBER", "your_account_number_here")
    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.content = [MagicMock(text=json.dumps({
        "data": {
            "accounts": [
                {"account_number": "11112222", "agentic_allowed": False},
                {"account_number": "33334444", "agentic_allowed": True}
            ]
        }
    }))]
    session.call_tool.return_value = mock_res

    account = await get_target_account(session)
    assert account == "33334444"
    session.call_tool.assert_called_once_with("get_accounts", arguments={})

@pytest.mark.asyncio
async def test_get_target_account_env_placeholder_keyword(monkeypatch):
    monkeypatch.setenv("ROBINHOOD_ACCOUNT_NUMBER", "placeholder_acc_123")
    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.content = [MagicMock(text=json.dumps({
        "data": {
            "accounts": [
                {"account_number": "55556666", "agentic_allowed": True}
            ]
        }
    }))]
    session.call_tool.return_value = mock_res

    account = await get_target_account(session)
    assert account == "55556666"

@pytest.mark.asyncio
async def test_get_target_account_fallback_primary(monkeypatch):
    monkeypatch.delenv("ROBINHOOD_ACCOUNT_NUMBER", raising=False)
    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.content = [MagicMock(text=json.dumps({
        "data": {
            "accounts": [
                {"account_number": "77778888", "agentic_allowed": False},
                {"account_number": "99990000", "agentic_allowed": False}
            ]
        }
    }))]
    session.call_tool.return_value = mock_res

    account = await get_target_account(session)
    assert account == "77778888"

@pytest.mark.asyncio
async def test_get_target_account_no_accounts(monkeypatch):
    monkeypatch.delenv("ROBINHOOD_ACCOUNT_NUMBER", raising=False)
    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.content = [MagicMock(text=json.dumps({
        "data": {
            "accounts": []
        }
    }))]
    session.call_tool.return_value = mock_res

    with pytest.raises(RuntimeError, match="No valid Robinhood brokerage accounts found."):
        await get_target_account(session)
