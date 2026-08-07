import os
import json
import datetime
from unittest.mock import patch, mock_open, MagicMock
import pytest
from trading_bot import TradingBot, STATE_FILE

def test_load_state_file_not_exists():
    """Test that when the state file does not exist, default state is returned."""
    with patch("os.path.exists", return_value=False):
        # We don't want to load or read anything
        bot = TradingBot(account_number="12345", dry_run=True)
        state = bot.state
        assert state["wash_sale_cooldowns"] == {}
        assert state["unsettled_buys"] == {}
        assert state["today_sales"] == []
        assert state["last_reset_date"] == str(datetime.date.today())

def test_load_state_valid_json_complete():
    """Test that valid and complete json in the state file is correctly loaded."""
    mock_data = {
        "wash_sale_cooldowns": {"AAPL": "2026-09-01"},
        "unsettled_buys": {"NVDA": {"buy_date": "2026-08-07", "amount": 10.0}},
        "today_sales": [10.5, 20.0],
        "last_reset_date": "2026-08-07"
    }
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
        bot = TradingBot(account_number="12345", dry_run=True)
        state = bot.state
        assert state == mock_data

def test_load_state_valid_json_missing_keys():
    """Test that missing keys are correctly initialized when state file exists but is partial."""
    mock_data = {
        "wash_sale_cooldowns": {"AAPL": "2026-09-01"}
        # other keys missing
    }
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
        bot = TradingBot(account_number="12345", dry_run=True)
        state = bot.state
        assert state["wash_sale_cooldowns"] == {"AAPL": "2026-09-01"}
        assert state["unsettled_buys"] == {}
        assert state["today_sales"] == []
        assert state["last_reset_date"] == str(datetime.date.today())

def test_load_state_invalid_json_exception():
    """Test that invalid JSON (causing json.load to raise Exception) falls back to defaults and logs error."""
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="invalid json data")), \
         patch("trading_bot.logger.error") as mock_log_error:
        bot = TradingBot(account_number="12345", dry_run=True)
        state = bot.state
        assert state["wash_sale_cooldowns"] == {}
        assert state["unsettled_buys"] == {}
        assert state["today_sales"] == []
        assert state["last_reset_date"] == str(datetime.date.today())
        # Verify that an error was logged
        mock_log_error.assert_called_once()
        assert "Error loading state file" in mock_log_error.call_args[0][0]

def test_load_state_io_error_exception():
    """Test that file read exceptions (e.g. PermissionError/IOError) fall back to defaults and log error."""
    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", side_effect=PermissionError("Permission denied")), \
         patch("trading_bot.logger.error") as mock_log_error:
        bot = TradingBot(account_number="12345", dry_run=True)
        state = bot.state
        assert state["wash_sale_cooldowns"] == {}
        assert state["unsettled_buys"] == {}
        assert state["today_sales"] == []
        assert state["last_reset_date"] == str(datetime.date.today())
        # Verify that an error was logged
        mock_log_error.assert_called_once()
        assert "Error loading state file" in mock_log_error.call_args[0][0]
