# Loads the trained model (saved in Stage 2) and scores setups.
import joblib
import config

model = joblib.load(config.MODEL_FILE)


def score(setups):
    """Add p_win (model probability) and a verdict to the setups table."""
    if setups.empty:
        return setups
    setups = setups.copy()
    setups["p_win"] = model.predict_proba(setups[config.FEATURES])[:, 1]
    setups["verdict"] = ["STRONG" if p >= config.MIN_PROB else "weak" for p in setups["p_win"]]
    return setups
