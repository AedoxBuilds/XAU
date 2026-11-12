"""Liquidity reference levels and wick-rejection sweep detection."""
import pandas as pd


def _confirmed_pivots(df: pd.DataFrame, swing: int):
    highs, lows = [], []
    for i in range(swing, len(df) - swing):
        window = df.iloc[i - swing:i + swing + 1]
        if df["high"].iloc[i] == window["high"].max():
            highs.append((i + swing, float(df["high"].iloc[i])))
        if df["low"].iloc[i] == window["low"].min():
            lows.append((i + swing, float(df["low"].iloc[i])))
    return highs, lows


def detect_liquidity(df: pd.DataFrame, swing: int = 3, tolerance: float = 0.0,
                     lookback: int = 100) -> dict:
    """Detect equal highs/lows and sweeps on the latest candle in the supplied frame."""
    empty = {"equal_highs": [], "equal_lows": [], "bsl": [], "ssl": [],
             "sweep": "NONE", "sweep_level": None}
    if df is None or df.empty or len(df) < 2 * swing + 3:
        return empty
    d = df.tail(lookback).copy().reset_index(drop=True)
    highs, lows = _confirmed_pivots(d, swing)
    tol = max(float(tolerance), 0.0)

    def clusters(points):
        levels = []
        for j, (_, price) in enumerate(points):
            matches = [p for _, p in points[max(0, j - 5):j] if abs(p - price) <= tol]
            if matches:
                levels.append(round(sum(matches + [price]) / (len(matches) + 1), 5))
        return sorted(set(levels))

    equal_highs, equal_lows = clusters(highs), clusters(lows)
    recent_highs = [p for pos, p in highs if pos < len(d) - 1][-10:]
    recent_lows = [p for pos, p in lows if pos < len(d) - 1][-10:]
    bsl, ssl = sorted(set(recent_highs + equal_highs)), sorted(set(recent_lows + equal_lows))
    last = d.iloc[-1]
    sweep, level = "NONE", None
    candidates = [x for x in bsl if float(last["high"]) > x and float(last["close"]) < x]
    if candidates:
        sweep, level = "BUY_SIDE_SWEPT", max(candidates)
    if sweep == "NONE":
        candidates = [x for x in ssl if float(last["low"]) < x and float(last["close"]) > x]
        if candidates:
            sweep, level = "SELL_SIDE_SWEPT", min(candidates)
    return {"equal_highs": equal_highs[-10:], "equal_lows": equal_lows[-10:],
            "bsl": bsl, "ssl": ssl, "sweep": sweep, "sweep_level": level}
