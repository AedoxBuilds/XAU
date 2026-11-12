import pandas as pd
from intelligence.data_quality import validate_ohlc
from intelligence.market_structure import detect_market_structure
from intelligence.liquidity import detect_liquidity
from strategy.risk_manager import size_from_loss_per_lot


def test_data_quality_accepts_valid_ohlc():
    idx = pd.date_range("2026-01-01", periods=5, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": [1, 2, 3, 4, 5], "high": [2, 3, 4, 5, 6],
                       "low": [0.5, 1.5, 2.5, 3.5, 4.5],
                       "close": [1.5, 2.5, 3.5, 4.5, 5.5]}, index=idx)
    assert validate_ohlc(df, 15)["ok"] is True


def test_data_quality_flags_impossible_candle():
    idx = pd.date_range("2026-01-01", periods=2, freq="15min", tz="UTC")
    df = pd.DataFrame({"open": [10, 10], "high": [9, 11], "low": [8, 9],
                       "close": [8.5, 10]}, index=idx)
    assert validate_ohlc(df)["ok"] is False


def test_risk_sizing_rounds_down_to_volume_step():
    result = size_from_loss_per_lot(100, 250, 0.01, 10, 0.01)
    assert result["volume"] == 0.4
    assert result["estimated_loss"] == 100.0


def test_risk_sizing_rejects_below_minimum():
    result = size_from_loss_per_lot(1, 500, 0.01, 10, 0.01)
    assert result["volume"] == 0.0


def test_market_structure_handles_short_history():
    result = detect_market_structure(pd.DataFrame({"high":[2,3],"low":[1,2],"close":[1.5,2.5]}))
    assert result["trend"] == "NEUTRAL"


def test_liquidity_handles_short_history():
    result = detect_liquidity(pd.DataFrame({"high":[2,3],"low":[1,2],"close":[1.5,2.5]}))
    assert result["sweep"] == "NONE"
