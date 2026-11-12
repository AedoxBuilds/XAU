"""Causal swing, BOS and CHoCH detection for OHLC candles."""
import pandas as pd


def detect_market_structure(df: pd.DataFrame, swing: int = 3) -> dict:
    if df is None or df.empty or len(df) < (2 * swing + 5):
        return {"trend": "NEUTRAL", "event": "NONE", "event_time": None,
                "swing_high": None, "swing_low": None, "bars_since_event": None}
    if swing < 1:
        raise ValueError("swing must be >= 1")
    data = df[["high", "low", "close"]].copy().reset_index()
    time_col = data.columns[0]
    last_high = last_low = None
    trend = 0
    latest_event, latest_event_time, latest_event_pos = "NONE", None, None
    broken_high = broken_low = None
    for i in range(len(data)):
        pivot_pos = i - swing
        if pivot_pos >= swing:
            window = data.iloc[pivot_pos - swing:pivot_pos + swing + 1]
            pivot = data.iloc[pivot_pos]
            if pivot["high"] == window["high"].max():
                last_high, broken_high = float(pivot["high"]), False
            if pivot["low"] == window["low"].min():
                last_low, broken_low = float(pivot["low"]), False
        close = float(data.iloc[i]["close"])
        if last_high is not None and not broken_high and close > last_high:
            event = "BOS" if trend >= 0 else "CHoCH"
            trend = 1
            latest_event, latest_event_time, latest_event_pos = event, data.iloc[i][time_col], i
            broken_high = True
        elif last_low is not None and not broken_low and close < last_low:
            event = "BOS" if trend <= 0 else "CHoCH"
            trend = -1
            latest_event, latest_event_time, latest_event_pos = event, data.iloc[i][time_col], i
            broken_low = True
    return {"trend": "BULLISH" if trend == 1 else "BEARISH" if trend == -1 else "NEUTRAL",
            "event": latest_event,
            "event_time": str(latest_event_time) if latest_event_time is not None else None,
            "swing_high": last_high, "swing_low": last_low,
            "bars_since_event": len(data) - 1 - latest_event_pos if latest_event_pos is not None else None}
