"""MT5-only live data adapter.

MT5 candle timestamps are UTC. We fetch each timeframe directly and request
start_pos=1 so the currently forming candle is never used for confirmation.
"""
import pandas as pd
import analysis
import config


def _to_ohlc(rates):
    if rates is None or len(rates) == 0:
        raise ValueError("MT5 returned no rates.")
    df = pd.DataFrame(rates)
    if "time" not in df:
        raise ValueError("MT5 rates do not contain a time field.")
    df["datetime"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.set_index("datetime").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df[["open", "high", "low", "close"]].astype(float).dropna()


def fetch_live():
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        if not mt5.symbol_select(config.MT5_SYMBOL, True):
            raise RuntimeError(
                f"Cannot select MT5 symbol {config.MT5_SYMBOL!r}: {mt5.last_error()}"
            )
        frames = {}
        for name, (constant_name, count) in config.MT5_TIMEFRAMES.items():
            timeframe = getattr(mt5, constant_name)
            rates = mt5.copy_rates_from_pos(config.MT5_SYMBOL, timeframe, 1, count)
            frame = _to_ohlc(rates)
            span = analysis.TF_SPAN[name]
            frame["avail"] = frame.index + span
            frames[name] = frame
        tick = mt5.symbol_info_tick(config.MT5_SYMBOL)
        if tick is None:
            raise RuntimeError(f"Could not fetch live tick: {mt5.last_error()}")
        quote = {
            "bid": float(tick.bid),
            "ask": float(tick.ask),
            "spread": float(tick.ask - tick.bid),
            "tick_time": pd.to_datetime(tick.time_msc, unit="ms", utc=True),
        }
    finally:
        mt5.shutdown()

    # Do not allow higher-timeframe candles that closed after the last closed M15 bar.
    cutoff = frames["M15"]["avail"].iloc[-1]
    for tf in ("W", "D", "H4"):
        frames[tf] = frames[tf][frames[tf]["avail"] <= cutoff]
        if frames[tf].empty:
            raise ValueError(f"No closed {tf} candles available at the latest M15 close.")
    return frames, quote


def fetch_demo():
    from pathlib import Path
    path = Path(config.RAW_CSV)
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(
            "MT5 is unavailable and no non-empty historical CSV exists. "
            "Refusing to display stale or synthetic data as a live market."
        )
    m15 = analysis.load_csv(str(path)).tail(12000)
    if len(m15) < 200:
        raise RuntimeError("Demo CSV has fewer than 200 candles; load more historical data.")
    return analysis.make_frames(m15), None


def get_frames():
    """Return (frames, quote, note); fallback data is always explicitly labelled."""
    try:
        frames, quote = fetch_live()
        return frames, quote, ""
    except Exception as live_error:
        try:
            frames, _ = fetch_demo()
            return frames, None, (
                "HISTORICAL CSV MODE — MT5 live connection failed: "
                f"{str(live_error)[:180]}. This is not a live quote."
            )
        except Exception as csv_error:
            raise RuntimeError(
                f"MT5 live data unavailable ({live_error}); historical fallback unavailable "
                f"({csv_error})."
            ) from live_error
