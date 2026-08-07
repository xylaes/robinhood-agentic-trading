import pytest
import pandas as pd
from trading_bot import TradingBot

@pytest.fixture
def bot():
    # Instantiate TradingBot in dry-run mode with a dummy account number
    return TradingBot(account_number="123456789", dry_run=True)

def test_evaluate_signals_empty_or_one_bar(bot):
    # Test len(df) < 2
    df_empty = pd.DataFrame()
    signal, close, rsi, ema_diff = bot.evaluate_signals(df_empty)
    assert signal == "hold"
    assert close == 0.0
    assert rsi == 0.0
    assert ema_diff == 50.0

    df_one = pd.DataFrame([{
        "close_price": 100.0,
        "rsi": 50.0,
        "ema9": 100.0,
        "ema21": 100.0
    }])
    signal, close, rsi, ema_diff = bot.evaluate_signals(df_one)
    assert signal == "hold"
    assert close == 0.0
    assert rsi == 0.0
    assert ema_diff == 50.0

def test_evaluate_signals_bullish_cross(bot):
    # prev_ema9 <= prev_ema21 (95 <= 100) and curr_ema9 > curr_ema21 (105 > 100)
    data = [
        {"close_price": 95.0, "rsi": 50.0, "ema9": 95.0, "ema21": 100.0},
        {"close_price": 105.0, "rsi": 50.0, "ema9": 105.0, "ema21": 100.0}
    ]
    df = pd.DataFrame(data)
    signal, close, rsi, ema_diff = bot.evaluate_signals(df)
    assert signal == "buy"
    assert close == 105.0
    assert rsi == 50.0
    assert ema_diff == 5.0

def test_evaluate_signals_bearish_cross(bot):
    # prev_ema9 >= prev_ema21 (105 >= 100) and curr_ema9 < curr_ema21 (95 < 100)
    data = [
        {"close_price": 105.0, "rsi": 50.0, "ema9": 105.0, "ema21": 100.0},
        {"close_price": 95.0, "rsi": 50.0, "ema9": 95.0, "ema21": 100.0}
    ]
    df = pd.DataFrame(data)
    signal, close, rsi, ema_diff = bot.evaluate_signals(df)
    assert signal == "sell"
    assert close == 95.0
    assert rsi == 50.0
    assert ema_diff == -5.0

def test_evaluate_signals_oversold_rsi(bot):
    # No crossover (90 <= 100 in both), but curr_rsi < 35 (30 < 35)
    data = [
        {"close_price": 90.0, "rsi": 50.0, "ema9": 90.0, "ema21": 100.0},
        {"close_price": 91.0, "rsi": 30.0, "ema9": 90.0, "ema21": 100.0}
    ]
    df = pd.DataFrame(data)
    signal, close, rsi, ema_diff = bot.evaluate_signals(df)
    assert signal == "buy"
    assert close == 91.0
    assert rsi == 30.0
    assert ema_diff == -10.0

def test_evaluate_signals_overbought_rsi(bot):
    # No crossover (110 >= 100 in both), but curr_rsi > 70 (75 > 70)
    data = [
        {"close_price": 110.0, "rsi": 50.0, "ema9": 110.0, "ema21": 100.0},
        {"close_price": 111.0, "rsi": 75.0, "ema9": 110.0, "ema21": 100.0}
    ]
    df = pd.DataFrame(data)
    signal, close, rsi, ema_diff = bot.evaluate_signals(df)
    assert signal == "sell"
    assert close == 111.0
    assert rsi == 75.0
    assert ema_diff == 10.0

def test_evaluate_signals_hold(bot):
    # No crossover, RSI is neutral (50)
    data = [
        {"close_price": 100.0, "rsi": 50.0, "ema9": 95.0, "ema21": 100.0},
        {"close_price": 101.0, "rsi": 50.0, "ema9": 96.0, "ema21": 100.0}
    ]
    df = pd.DataFrame(data)
    signal, close, rsi, ema_diff = bot.evaluate_signals(df)
    assert signal == "hold"
    assert close == 101.0
    assert rsi == 50.0
    assert ema_diff == -4.0
