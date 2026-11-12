# Aedox Gold Analysis Agent

MT5-backed XAU/USD analysis dashboard. This application is **analysis-only**: it does not place trades.

## Current analysis flow

MT5 closed candles -> OHLC validation -> Weekly/Daily/H4 bias -> Daily/H4 OB and FVG zones -> M15 confirmation -> Random Forest setup score -> dashboard.

The upgrade branch adds:
- Direct MT5 candle retrieval for W1, D1, H4 and M15.
- UTC-aware timestamps (no manually hardcoded broker offset).
- Exclusion of the currently forming candle from analysis.
- Data-quality checks for duplicate timestamps, invalid OHLC ranges and missing data.
- Separate market-structure engine for confirmed swing/BOS/CHoCH context.
- Liquidity reference levels and wick-rejection sweep detection.
- Broker-aware position-sizing helper using MT5 `order_calc_profit` and broker volume constraints.
- Dashboard panels for bid/ask/spread, structure and liquidity.
- Initial unit tests for data validation and risk sizing.

## Requirements

- Windows desktop with MetaTrader 5 terminal installed and logged in.
- Python version compatible with the MetaTrader5 package.
- The broker's exact gold symbol configured in `config.py` (often XAUUSD, XAUUSDm, GOLD, etc.).

Install from this directory:

```bash
python -m pip install -r requirements.txt
```

## Run the dashboard

```bash
python run.py
```

Open http://127.0.0.1:5000.

The MT5 terminal must be running and connected. The dashboard reads closed candles and current bid/ask quotes. If MT5 is unavailable, the application only uses a historical CSV if it exists and contains enough data; it labels that mode clearly. If neither source is available, it fails visibly instead of presenting synthetic data as live market data.

## Historical training pipeline

The training pipeline expects a real 15-minute XAU/USD OHLC CSV at `data/raw/gold_15m.csv` with columns:

`datetime, open, high, low, close`

Use broker-exported data with a consistent symbol and timestamp basis. Aim for multiple years of history, but inspect quality and gaps first.

```bash
python stage1_preprocess.py
python stage2_train.py
python run.py
```

**Important:** Never train or evaluate the model on synthetic sample candles and then interpret its scores as live-market probabilities. The committed sample/setup statistics are historical project artifacts, not verified current performance. The raw CSV in the repository may be empty; supply genuine MT5 history before rebuilding the model.

## Tests

From this directory:

```bash
python -m pytest -q
```

## Important limitations

- BOS/CHoCH and liquidity levels are rule-based context, not guaranteed reversal signals.
- The existing Random Forest score is a classification score, not a calibrated probability of winning.
- Existing backtest labels need further audit for same-candle SL/TP collisions, spread, commissions, slippage and purged chronological validation.
- Economic-calendar, DXY, Treasury-yield and news feeds are not yet connected. Do not infer fundamental conditions from missing data.
- Position sizing helper is not an order-execution feature. It should be validated against the broker's symbol contract specifications and account currency.
- No automated order execution is enabled.

## Development branch

`feature/aedox-intelligence-upgrade`
