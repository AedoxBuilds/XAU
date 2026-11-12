# Gold Analysis Agent (analysis only, you place the trades)

Flow: Weekly bias -> Daily / 4H order blocks + FVGs -> 15m confirmation candle -> model scores the setup.

## IMPORTANT
data/raw/gold_15m.csv is SYNTHETIC SAMPLE DATA, only so the code runs.
Replace it with your real 15-minute gold data (columns: datetime, open, high, low, close).
Use 3-5+ years so there are enough setups to train on.

## Run order (always from this folder)
1. pip install -r requirements.txt
2. python stage1_preprocess.py   -> data/processed/setups.csv
3. python stage2_train.py        -> models/gold_model.pkl + quant stats
4. python run.py                 -> open http://127.0.0.1:5000

If live data fails, the dashboard shows a DEMO MODE banner (it uses the end of your CSV).
All strategy settings (RR, swing size, OB rule, ...) are in config.py.
