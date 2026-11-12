import time
import MetaTrader5 as mt5
import pandas as pd
import config

if not mt5.initialize():
    raise SystemExit("MT5 is not open or not logged in: " + str(mt5.last_error()))
mt5.symbol_select(config.MT5_SYMBOL, True)
time.sleep(3)

rates = None
for count in [100000, 50000, 30000, 20000, 10000, 5000]:
    rates = mt5.copy_rates_from_pos(config.MT5_SYMBOL, mt5.TIMEFRAME_M15, 1, count)
    if rates is not None and len(rates) > 0:
        print("MT5 gave", len(rates), "candles when asking for", count)
        break
    print("Asked for", count, "-> nothing. MT5 says:", mt5.last_error())
    time.sleep(2)
mt5.shutdown()

if rates is None or len(rates) == 0:
    raise SystemExit("Still no data. Open the XAUUSD M15 chart in MT5, scroll left, then run again.")

df = pd.DataFrame(rates)
df["datetime"] = pd.to_datetime(df["time"], unit="s") - pd.Timedelta(hours=config.MT5_SERVER_OFFSET_HOURS)
df = df[["datetime", "open", "high", "low", "close"]]
df.to_csv(config.RAW_CSV, index=False)
print("Saved", len(df), "candles:", df["datetime"].iloc[0], "->", df["datetime"].iloc[-1])