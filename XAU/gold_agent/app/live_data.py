import pandas as pd
import analysis
import config


def _to_df(rates):
    df = pd.DataFrame(rates)
    df["datetime"] = pd.to_datetime(df["time"], unit="s") - pd.Timedelta(hours=config.MT5_SERVER_OFFSET_HOURS)
    return df.set_index("datetime")[["open", "high", "low", "close"]].astype(float)


def fetch_live():
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError("MT5 is not open or not logged in: %s" % (mt5.last_error(),))
    try:
        mt5.symbol_select(config.MT5_SYMBOL, True)
        h1 = mt5.copy_rates_from_pos(config.MT5_SYMBOL, mt5.TIMEFRAME_H1, 1, 20000)
        m15 = mt5.copy_rates_from_pos(config.MT5_SYMBOL, mt5.TIMEFRAME_M15, 1, 15000)
    finally:
        mt5.shutdown()
    if h1 is None or m15 is None or len(h1) < 200 or len(m15) < 200:
        raise ValueError("MT5 gave no data for symbol '%s' (check the name in Market Watch)" % config.MT5_SYMBOL)
    h1, m15 = _to_df(h1), _to_df(m15)

    frames = {tf: analysis.resample_ohlc(h1, tf) for tf in ["W", "D", "H4"]}
    frames["M15"] = analysis.resample_ohlc(m15, "M15")
    cutoff = h1.index[-1] + pd.Timedelta(hours=1)
    for tf in ["W", "D", "H4"]:
        frames[tf] = frames[tf][frames[tf]["avail"] <= cutoff]
    return frames


def fetch_demo():
    m15 = analysis.load_csv(config.RAW_CSV).tail(12000)
    return analysis.make_frames(m15)


def get_frames():
    """Returns (frames, note). note is shown on the dashboard in demo mode."""
    try:
        return fetch_live(), ""
    except Exception as e:
        return fetch_demo(), ("DEMO MODE - live data failed (%s). Showing the end of your CSV, "
                              "not the real market." % str(e)[:150])