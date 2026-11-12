# ============================================================
# config.py - centralized Gold Analysis Agent settings
# ============================================================
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RAW_CSV = str(BASE_DIR / "data/raw/gold_15m.csv")
PROCESSED_CSV = str(BASE_DIR / "data/processed/setups.csv")
MODEL_FILE = str(BASE_DIR / "models/gold_model.pkl")
STATS_FILE = str(BASE_DIR / "models/quant_stats.csv")
METRICS_FILE = str(BASE_DIR / "models/model_metrics.csv")
CHART_FILE = str(BASE_DIR / "app/static/chart.png")

# Strategy settings (preserve existing strategy until new rules are validated)
RR = 2.0
SWING_N = {"W": 1, "D": 2, "H4": 2}
ATR_PERIOD = 14
OB_DISPLACEMENT = 1.2
MIN_FVG_ATR = 0.1
SL_BUFFER_ATR = 0.1
MIN_RISK_ATR = 0.3
MAX_RISK_ATR = 5.0
MAX_HOLD_BARS = 96
ZONE_MAX_AGE = {"D": 30, "H4": 60}

# Model
TEST_SIZE = 0.2
MIN_PROB = 0.5
FEATURES = [
    "direction", "kind_ob", "tf_daily", "d_rel", "h4_rel",
    "zone_size_atr", "risk_atr", "atr", "hour", "session", "dow",
    "confluence", "prior_touches", "zone_age_hours",
]

# Live market data
MT5_SYMBOL = "XAUUSD"  # Verify exact broker symbol in MT5 Market Watch.
MT5_TIMEFRAMES = {
    "W": ("TIMEFRAME_W1", 1200),
    "D": ("TIMEFRAME_D1", 3000),
    "H4": ("TIMEFRAME_H4", 6000),
    "M15": ("TIMEFRAME_M15", 12000),
}
REFRESH_SECONDS = 60
CHART_BARS = 120
LAST_BARS = 3
LIQUIDITY_SWING = 3
LIQUIDITY_LOOKBACK = 200
LIQUIDITY_ATR_TOLERANCE = 0.10
