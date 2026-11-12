"""Market-data quality checks. These checks report issues; they do not silently repair prices."""
import pandas as pd

REQUIRED_OHLC = ("open", "high", "low", "close")


def validate_ohlc(df: pd.DataFrame, timeframe_minutes: int | None = None) -> dict:
    """Return a JSON-friendly quality report for an OHLC DataFrame indexed by time."""
    issues = []
    if df is None or df.empty:
        return {"ok": False, "rows": 0, "issues": ["No candle data received."]}
    missing = [c for c in REQUIRED_OHLC if c not in df.columns]
    if missing:
        return {"ok": False, "rows": len(df), "issues": [f"Missing OHLC columns: {missing}"]}
    if not isinstance(df.index, pd.DatetimeIndex):
        issues.append("Index is not a DatetimeIndex.")
    else:
        if df.index.has_duplicates:
            issues.append(f"{int(df.index.duplicated().sum())} duplicate timestamps.")
        if not df.index.is_monotonic_increasing:
            issues.append("Timestamps are not sorted ascending.")
        if df.index.tz is None:
            issues.append("Timestamps are timezone-naive; normalize to UTC.")
    prices = df.loc[:, REQUIRED_OHLC].apply(pd.to_numeric, errors="coerce")
    if prices.isna().any().any():
        issues.append("OHLC contains missing or non-numeric values.")
    if (prices <= 0).any().any():
        issues.append("OHLC contains zero or negative prices.")
    invalid = ((prices["high"] < prices[["open", "close", "low"]].max(axis=1))
               | (prices["low"] > prices[["open", "close", "high"]].min(axis=1)))
    if invalid.any():
        issues.append(f"{int(invalid.sum())} candles have impossible OHLC ranges.")
    gaps = 0
    if timeframe_minutes and isinstance(df.index, pd.DatetimeIndex) and len(df) > 1:
        delta = df.index.to_series().diff().dropna()
        gaps = int((delta > pd.Timedelta(minutes=timeframe_minutes) * 3).sum())
    return {"ok": not issues, "rows": int(len(df)), "start": str(df.index.min()),
            "end": str(df.index.max()), "large_gaps": gaps, "issues": issues}
