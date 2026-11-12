# ============================================================
# STAGE 1 - load the 15m CSV, build W/D/H4 candles, find every
# setup (bias + OB/FVG + 15m confirmation), label the result,
# and save the processed CSV.
# Run:  python stage1_preprocess.py
# ============================================================
import analysis
import config

print("Loading", config.RAW_CSV)
m15 = analysis.load_csv(config.RAW_CSV)
print("15m candles:", len(m15), "|", m15.index[0], "->", m15.index[-1])

frames = analysis.prep_frames(analysis.make_frames(m15))
for tf in ["W", "D", "H4"]:
    print(tf, "candles:", len(frames[tf]))

setups = analysis.build_setups(frames, label=True)
print("Setups found:", len(setups))
print("Win rate (1:%s): %.1f%%" % (config.RR, (setups["win"] == 1).mean() * 100))
print(setups["kind"].value_counts().to_string())

setups.to_csv(config.PROCESSED_CSV, index=False)
print("Saved ->", config.PROCESSED_CSV)
