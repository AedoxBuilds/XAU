# ============================================================
# STAGE 2 - load processed setups, split by TIME (no shuffle),
# train, evaluate, run the quant backtest, save model + stats.
# Run:  python stage2_train.py
# ============================================================
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
import analysis
import config

df = pd.read_csv(config.PROCESSED_CSV, parse_dates=["time"])
df = df.sort_values("time").reset_index(drop=True)
print("Setups:", len(df))
if len(df) < 300:
    print("WARNING: fewer than 300 setups - the model will be unreliable. Use more history (3-5+ years of 15m data).")

X = df[config.FEATURES]
y = df["win"].astype(int)

# time order: oldest rows train, newest rows test (shuffle=False on purpose)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=config.TEST_SIZE, shuffle=False)

model = RandomForestClassifier(n_estimators=300, max_depth=6, min_samples_leaf=20,
                               class_weight="balanced", random_state=42)
model.fit(X_train, y_train)

prob = model.predict_proba(X_test)[:, 1]
pred = (prob >= config.MIN_PROB).astype(int)

print("\nAccuracy:", round(accuracy_score(y_test, pred), 3))
auc = roc_auc_score(y_test, prob) if y_test.nunique() == 2 else float("nan")
print("ROC AUC :", round(auc, 3), "(0.5 = no better than guessing)")
print(confusion_matrix(y_test, pred))
print(classification_report(y_test, pred, zero_division=0))
print("Feature importance:")
print(pd.Series(model.feature_importances_, index=config.FEATURES)
      .sort_values(ascending=False).round(3).to_string())

# ---- quant check on the TEST period: all setups vs model-filtered setups ----
test = df.loc[X_test.index].copy()
test["p_win"] = prob
picked = test[test["p_win"] >= config.MIN_PROB]
all_s, pick_s = analysis._stats(test), (analysis._stats(picked) if len(picked) else None)
print("\nTEST period  ALL setups :", {k: round(float(v), 2) for k, v in all_s.items()})
if pick_s:
    print("TEST period  MODEL picks:", {k: round(float(v), 2) for k, v in pick_s.items()})
print("(expectancy_R above 0 = profitable on average, below 0 = losing)")

# ---- save everything the dashboard needs ----
analysis.quant_table(df).round(2).to_csv(config.STATS_FILE, index=False)
metrics = {
    "setups_total": len(df), "train_rows": len(X_train), "test_rows": len(X_test),
    "accuracy": accuracy_score(y_test, pred), "roc_auc": auc,
    "test_all_win_rate": all_s["win_rate_%"], "test_all_expectancy_R": all_s["expectancy_R"],
    "test_picked_trades": pick_s["trades"] if pick_s else 0,
    "test_picked_win_rate": pick_s["win_rate_%"] if pick_s else float("nan"),
    "test_picked_expectancy_R": pick_s["expectancy_R"] if pick_s else float("nan"),
}
pd.DataFrame([metrics]).round(3).to_csv(config.METRICS_FILE, index=False)
joblib.dump(model, config.MODEL_FILE)
print("\nSaved ->", config.MODEL_FILE, config.STATS_FILE, config.METRICS_FILE)
