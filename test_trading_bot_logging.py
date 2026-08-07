import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import logging
import asyncio

from trading_bot import TradingBot

class TestTradingBotLogging(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Configure logging to capture output
        self.log_handler = logging.Handler()
        self.log_messages = []
        self.log_handler.emit = lambda record: self.log_messages.append(record.getMessage())

        self.logger = logging.getLogger("trading_bot")
        self.logger.addHandler(self.log_handler)
        self.logger.setLevel(logging.INFO)

    def tearDown(self):
        self.logger.removeHandler(self.log_handler)

    async def test_buy_position_does_not_log_review_data(self):
        # Create bot with dry_run = True (dry_run doesn't place live trades)
        bot = TradingBot(account_number="123456789", dry_run=True)

        # Mock session and its call_tool response
        mock_session = AsyncMock()

        mock_content = MagicMock()
        # Sensitive review data returned from the broker simulation tool
        sensitive_review_data = {
            "account_number": "123456789",
            "available_buying_power": 50000.00,
            "secret_broker_token": "super-secret-token-123",
            "regulatory_fees": 0.04
        }
        mock_content.text = json.dumps(sensitive_review_data)

        mock_res = MagicMock()
        mock_res.content = [mock_content]
        mock_session.call_tool.return_return_value = mock_res
        mock_session.call_tool.side_effect = lambda tool_name, arguments=None: mock_res

        # Call buy_position
        await bot.buy_position(
            session=mock_session,
            symbol="NVDA",
            usd_amount=10.00,
            current_price=120.00,
            is_settled=True
        )

        # Check logs
        found_completed_msg = False
        found_sensitive_data = False

        for msg in self.log_messages:
            if "Pre-trade simulation review completed successfully." in msg:
                found_completed_msg = True
            if "super-secret-token-123" in msg or "available_buying_power" in msg:
                found_sensitive_data = True

        self.assertTrue(found_completed_msg, "Should log success completion message.")
        self.assertFalse(found_sensitive_data, "Should NOT log any sensitive broker review_data.")

    async def test_sell_position_does_not_log_review_data(self):
        # Create bot with dry_run = True
        bot = TradingBot(account_number="123456789", dry_run=True)

        # Mock session and its call_tool response
        mock_session = AsyncMock()

        mock_content = MagicMock()
        sensitive_review_data = {
            "account_number": "123456789",
            "available_buying_power": 50000.00,
            "secret_broker_token": "super-secret-token-123",
            "regulatory_fees": 0.04
        }
        mock_content.text = json.dumps(sensitive_review_data)

        mock_res = MagicMock()
        mock_res.content = [mock_content]
        mock_session.call_tool.side_effect = lambda tool_name, arguments=None: mock_res

        # Call sell_position
        await bot.sell_position(
            session=mock_session,
            symbol="NVDA",
            quantity=0.083,
            current_price=120.00,
            reason="signal",
            avg_cost=100.00
        )

        # Check logs
        found_completed_msg = False
        found_sensitive_data = False

        for msg in self.log_messages:
            if "Pre-trade simulation review completed successfully." in msg:
                found_completed_msg = True
            if "super-secret-token-123" in msg or "available_buying_power" in msg:
                found_sensitive_data = True

        self.assertTrue(found_completed_msg, "Should log success completion message.")
        self.assertFalse(found_sensitive_data, "Should NOT log any sensitive broker review_data.")

if __name__ == "__main__":
    unittest.main()
