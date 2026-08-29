import asyncio
import json
import pytest
from trading_bot import TradingBot

class MockContent:
    def __init__(self, text):
        self.text = text

class MockResponse:
    def __init__(self, text):
        self.content = [MockContent(text)]

class MockSession:
    def __init__(self, fail_symbols=None):
        self.fail_symbols = fail_symbols or set()
        self.called_symbols = []

    async def call_tool(self, name, arguments):
        if name == "get_portfolio":
            return MockResponse(json.dumps({
                "data": {
                    "buying_power": {"buying_power": "1000.0"},
                    "equity": "1000.0",
                    "settled_cash": "500.0"
                }
            }))
        elif name == "get_equity_positions":
            return MockResponse(json.dumps({"data": {"positions": []}}))
        elif name == "get_equity_quotes":
            results = []
            for s in arguments.get("symbols", []):
                results.append({
                    "quote": {
                        "symbol": s,
                        "last_trade_price": "100.0",
                        "bid_price": "99.5",
                        "ask_price": "100.5"
                    }
                })
            return MockResponse(json.dumps({"data": {"results": results}}))
        elif name == "get_equity_historicals":
            symbol = arguments["symbols"][0]
            self.called_symbols.append(symbol)
            if symbol in self.fail_symbols:
                raise RuntimeError(f"Failed to fetch {symbol}")

            bars = []
            for i in range(20):
                bars.append({
                    "begins_at": f"2026-01-01T{i:02d}:00:00Z",
                    "close_price": str(100.0 + i)
                })
            return MockResponse(json.dumps({
                "data": {
                    "results": [{"symbol": symbol, "bars": bars}]
                }
            }))
        return MockResponse(json.dumps({"data": {}}))

@pytest.mark.asyncio
async def test_concurrent_historicals_fetching():
    bot = TradingBot(account_number="12345678", dry_run=True)
    session = MockSession(fail_symbols={"FAIL_SYM"})

    bot.resolve_watchlist = lambda sess: asyncio.sleep(0, result=["AAPL", "FAIL_SYM", "MSFT"])
    bot.is_near_earnings = lambda sess, sym: asyncio.sleep(0, result=False)

    await bot.execute_run(session)

    assert set(session.called_symbols) == {"AAPL", "FAIL_SYM", "MSFT"}
