import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from trading_bot import TradingBot

@pytest.fixture
def dummy_bot():
    """Returns a TradingBot instance with load_state mocked to avoid touching disk."""
    with patch.object(TradingBot, 'load_state', return_value={
        "wash_sale_cooldowns": {},
        "unsettled_buys": {},
        "today_sales": [],
        "last_reset_date": "2025-01-01"
    }):
        bot = TradingBot(account_number="12345", dry_run=True)
        yield bot

def test_compute_indicators_standard(dummy_bot):
    """Test compute_indicators with a standard sequence of 25 bars."""
    bars = []
    # Generate 25 data points with some variation
    for i in range(25):
        bars.append({"close_price": float(100 + (i % 5) * 2 - (i % 3) * 1)})

    df = dummy_bot.compute_indicators(bars)

    # Assert return type and columns
    assert isinstance(df, pd.DataFrame)
    assert "close_price" in df.columns
    assert "ema9" in df.columns
    assert "ema21" in df.columns
    assert "rsi" in df.columns

    # Assert all values are calculated and non-null (except first index of rsi due to diff)
    assert len(df) == 25
    assert not df["ema9"].isna().any()
    assert not df["ema21"].isna().any()

    # RSI index 0 is always NaN because of price diff
    assert pd.isna(df.loc[0, "rsi"])
    assert not df.loc[1:, "rsi"].isna().any()

def test_compute_indicators_string_prices(dummy_bot):
    """Test that close prices as strings are correctly parsed to float."""
    bars = [
        {"close_price": "100.50"},
        {"close_price": "101.00"},
        {"close_price": "102.50"},
    ]
    df = dummy_bot.compute_indicators(bars)

    assert pd.api.types.is_float_dtype(df["close_price"])
    assert df.loc[0, "close_price"] == 100.50
    assert df.loc[1, "close_price"] == 101.00
    assert df.loc[2, "close_price"] == 102.50

def test_compute_indicators_empty_and_small_inputs(dummy_bot):
    """Test compute_indicators behavior on empty and very small inputs."""
    # Empty input will raise a KeyError because "close_price" won't exist in an empty DataFrame.
    # We should document this behavior or verify it raises KeyError.
    with pytest.raises(KeyError):
        dummy_bot.compute_indicators([])

    # 1 bar input: EMA should be calculated, RSI should be NaN
    bars = [{"close_price": 10.0}]
    df = dummy_bot.compute_indicators(bars)
    assert len(df) == 1
    assert df.loc[0, "ema9"] == 10.0
    assert df.loc[0, "ema21"] == 10.0
    assert pd.isna(df.loc[0, "rsi"])

def test_compute_indicators_flat_prices(dummy_bot):
    """Test compute_indicators when prices remain completely flat."""
    bars = [{"close_price": 100.0} for _ in range(15)]
    df = dummy_bot.compute_indicators(bars)

    # EMA should equal the flat close price
    for val in df["ema9"]:
        assert val == pytest.approx(100.0)
    for val in df["ema21"]:
        assert val == pytest.approx(100.0)

    # Since there are no price changes, gains and losses are zero.
    # rs = 0 / 0 = NaN, so RSI is NaN
    assert df["rsi"].isna().all()

def test_compute_indicators_ema_mathematical_correctness(dummy_bot):
    """Manually trace and verify EMA9 and EMA21 calculation correctness."""
    bars = [
        {"close_price": 10.0},
        {"close_price": 11.0},
        {"close_price": 12.0},
        {"close_price": 13.0}
    ]
    df = dummy_bot.compute_indicators(bars)

    # Hand-computed EMA9 (span=9, alpha=0.2):
    # y0 = 10.0
    # y1 = 0.8 * 10.0 + 0.2 * 11.0 = 10.2
    # y2 = 0.8 * 10.2 + 0.2 * 12.0 = 10.56
    # y3 = 0.8 * 10.56 + 0.2 * 13.0 = 11.048
    expected_ema9 = [10.0, 10.2, 10.56, 11.048]
    np.testing.assert_allclose(df["ema9"], expected_ema9, rtol=1e-5)

    # Hand-computed EMA21 (span=21, alpha=2/22 = 1/11):
    # y0 = 10.0
    # y1 = (10/11) * 10.0 + (1/11) * 11.0 = 111/11 = 10.09090909
    # y2 = (10/11) * (111/11) + (1/11) * 12.0 = 1242/121 = 10.26446281
    # y3 = (10/11) * (1242/121) + (1/11) * 13.0 = 13993/1331 = 10.51314801
    expected_ema21 = [
        10.0,
        111/11,
        1242/121,
        13993/1331
    ]
    np.testing.assert_allclose(df["ema21"], expected_ema21, rtol=1e-5)

def test_compute_indicators_rsi_mathematical_correctness(dummy_bot):
    """Manually trace and verify 14 RSI calculation correctness using a known sequence."""
    bars = [
        {"close_price": 10.0},
        {"close_price": 11.0},
        {"close_price": 12.0},
        {"close_price": 11.0}
    ]
    df = dummy_bot.compute_indicators(bars)

    # Hand-computed RSI (com=13, alpha=1/14):
    # delta = [NaN, 1.0, 1.0, -1.0]
    # gain = [NaN, 1.0, 1.0, 0.0]
    # loss = [NaN, 0.0, 0.0, 1.0]
    #
    # ewm(com=13, adjust=False).mean() starts at the first non-NaN element (index 1).
    # gain_ewm:
    # idx 1: 1.0
    # idx 2: (13/14) * 1.0 + (1/14) * 1.0 = 1.0
    # idx 3: (13/14) * 1.0 + (1/14) * 0.0 = 13/14
    #
    # loss_ewm:
    # idx 1: 0.0
    # idx 2: (13/14) * 0.0 + (1/14) * 0.0 = 0.0
    # idx 3: (13/14) * 0.0 + (1/14) * 1.0 = 1/14
    #
    # rs at idx 3: (13/14) / (1/14) = 13
    # rsi at idx 3: 100 - (100 / (1 + 13)) = 100 - 100/14 = 92.85714
    assert pd.isna(df.loc[0, "rsi"])

    # At index 1 and 2, loss is 0.0, which makes rs = gain / 0 = inf.
    # 100 - (100 / (1 + inf)) = 100.0
    assert df.loc[1, "rsi"] == pytest.approx(100.0)
    assert df.loc[2, "rsi"] == pytest.approx(100.0)

    # At index 3, RSI should be approx 92.85714
    assert df.loc[3, "rsi"] == pytest.approx(92.85714, rel=1e-4)

def test_compute_indicators_perfect_uptrend_and_downtrend(dummy_bot):
    """Test RSI behavior under extreme trends."""
    # Perfect uptrend: RSI should quickly peg to 100
    up_bars = [{"close_price": float(10 + i)} for i in range(20)]
    df_up = dummy_bot.compute_indicators(up_bars)
    # Beyond index 0, rsi should be exactly 100
    for rsi_val in df_up.loc[1:, "rsi"]:
        assert rsi_val == pytest.approx(100.0)

    # Perfect downtrend: RSI should quickly peg to 0
    down_bars = [{"close_price": float(100 - i)} for i in range(20)]
    df_down = dummy_bot.compute_indicators(down_bars)
    # Beyond index 0, rsi should be exactly 0
    for rsi_val in df_down.loc[1:, "rsi"]:
        assert rsi_val == pytest.approx(0.0)
