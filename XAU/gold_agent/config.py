# ============================================================
# config.py  -  every setting of the project in ONE place
# (run all files from the project root folder)
# ============================================================

# ---------- file paths ----------
RAW_CSV = "data/raw/gold_15m.csv"          # your 15-minute gold candles
PROCESSED_CSV = "data/processed/setups.csv"
MODEL_FILE = "models/gold_model.pkl"
STATS_FILE = "models/quant_stats.csv"
METRICS_FILE = "models/model_metrics.csv"
CHART_FILE = "app/static/chart.png"

# ---------- strategy settings (change these to match YOUR rules) ----------
RR = 2.0                  # reward : risk  (2.0 means 1:2)
SWING_N = {"W": 1, "D": 2, "H4": 2}   # candles on each side of a swing high/low
ATR_PERIOD = 14
OB_DISPLACEMENT = 1.2     # order block: next candle body must be >= 1.2 x ATR
MIN_FVG_ATR = 0.1         # ignore tiny FVGs (smaller than 0.1 x ATR)
SL_BUFFER_ATR = 0.1       # stop-loss buffer beyond the zone / candle
MIN_RISK_ATR = 0.3        # skip setups with a stop that is too tight
MAX_RISK_ATR = 5.0        # skip setups with a stop that is too wide
MAX_HOLD_BARS = 96        # a trade is closed after 96 x 15min = 24 hours
ZONE_MAX_AGE = {"D": 30, "H4": 60}    # zone expires after 30 days / 60 four-hour candles

# ---------- model ----------
TEST_SIZE = 0.2           # last 20% of the time = test (no shuffle)
MIN_PROB = 0.5            # model probability needed to call a setup "strong"
FEATURES = [
    "direction", "kind_ob", "tf_daily", "d_rel", "h4_rel",
    "zone_size_atr", "risk_atr", "atr", "hour", "session", "dow",
    "confluence", "prior_touches", "zone_age_hours",
]

# ---------- live ----------
LIVE_SYMBOL = "GC=F"      # gold futures on Yahoo Finance
REFRESH_SECONDS = 60      # dashboard refresh time
CHART_BARS = 120          # candles shown on the chart
LAST_BARS = 3             # a setup counts as "live" if it appeared in the last 3 candles

MT5_SYMBOL = "XAUUSD"
MT5_SERVER_OFFSET_HOURS = 2
