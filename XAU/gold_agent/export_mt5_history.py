"""Export closed M15 candles from MT5 to the project's UTC CSV format.

This script only reads market history. It does not send, modify, or close orders.
Run from the gold_agent directory after opening/logging in to the MT5 terminal.
"""
import time
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd
import config


def main():
    if not mt5.initialize():
        raise SystemExit(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        if not mt5.symbol_select(config.MT5_SYMBOL, True):
            raise SystemExit(f"Cannot select {config.MT5_SYMBOL}: {mt5.last_error()}")
        time.sleep(2)
        rates = None
        for count in (100000, 50000, 30000, 20000, 10000, 5000):
            rates = mt5.copy_rates_from_pos(config.MT5_SYMBOL, mt5.TIMEFRAME_M15, 1, count)
            if rates is not None and len(rates):
                print(f"MT5 returned {len(rates)} closed candles (requested {count}).")
                break
            print(f"Requested {count}: {mt5.last_error()}")
            time.sleep(1)
        if rates is None or len(rates) == 0:
            raise SystemExit(
                "No history returned. Open the configured symbol's M15 chart in MT5, "
                "scroll left to load history, then retry."
            )
        df = pd.DataFrame(rates)
        df["datetime"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df[["datetime", "open", "high", "low", "close"]]
        df = df.drop_duplicates("datetime").sort_values("datetime")
        out = Path(config.RAW_CSV)
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        print(f"Saved {len(df)} UTC candles to {out}")
        print(f"Range: {df['datetime'].iloc[0]} -> {df['datetime'].iloc[-1]}")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
