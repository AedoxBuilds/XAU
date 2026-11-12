# ============================================================
# Live analysis orchestration: MT5 -> technical engines -> model -> UI
# ============================================================
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import analysis
import config
from intelligence.market_structure import detect_market_structure
from intelligence.liquidity import detect_liquidity
from intelligence.data_quality import validate_ohlc
from .live_data import get_frames
from .model import score

BIAS_NAME = {1: "Bullish", -1: "Bearish", 0: "Neutral"}


def draw_chart(m15, zones, setups):
    d = m15.tail(config.CHART_BARS)
    o, h, l, c = (d[x].values for x in ["open", "high", "low", "close"])
    fig, ax = plt.subplots(figsize=(11, 5))
    for i in range(len(d)):
        col = "#2e9e5b" if c[i] >= o[i] else "#d94b4b"
        ax.vlines(i, l[i], h[i], color=col, linewidth=1)
        ax.bar(i, max(abs(c[i] - o[i]), 0.01), bottom=min(o[i], c[i]), color=col, width=0.6)
    ymin, ymax = l.min(), h.max()
    pad = max((ymax - ymin) * 0.1, 0.01)
    ax.set_ylim(ymin - pad, ymax + pad)
    for z in zones.itertuples():
        if z.top < ymin - pad or z.bottom > ymax + pad:
            continue
        col = "#2e9e5b" if z.direction == 1 else "#d94b4b"
        ax.axhspan(z.bottom, z.top, color=col, alpha=0.18 if z.aligned else 0.07)
        ax.text(0.5, z.top, " %s %s" % (z.tf, z.kind), fontsize=8, va="bottom")
    if len(setups):
        s = setups.iloc[-1]
        for val, col, name in [(s["entry"], "blue", "entry"), (s["stop"], "red", "SL"),
                               (s["target"], "green", "TP")]:
            ax.axhline(val, color=col, linestyle="--", linewidth=1)
            ax.text(len(d) - 1, val, " %s %.2f" % (name, val), color=col, fontsize=8)
    ticks = np.linspace(0, len(d) - 1, min(6, len(d))).astype(int)
    ax.set_xticks(ticks)
    ax.set_xticklabels([d.index[t].strftime("%d %b %H:%M") for t in ticks], fontsize=8)
    ax.set_title("Gold 15m | Active D/H4 zones | Latest closed candles")
    ax.grid(alpha=0.2)
    fig.savefig(config.CHART_FILE, dpi=110, bbox_inches="tight")
    plt.close(fig)


def read_csv_or_empty(path):
    try:
        return pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()


def _structure_row(label, frame):
    result = detect_market_structure(frame, swing=config.LIQUIDITY_SWING)
    return {"timeframe": label, **result}


def run_analysis():
    frames, quote, note = get_frames()
    frames = analysis.prep_frames(frames)
    m15 = frames["M15"]

    quality = {
        "M15": validate_ohlc(m15, 15),
        "H4": validate_ohlc(frames["H4"], 240),
        "D1": validate_ohlc(frames["D"], 1440),
    }
    invalid = [tf for tf, report in quality.items() if not report["ok"]]
    if invalid:
        raise ValueError("Market data failed OHLC validation for: " + ", ".join(invalid))

    biases = [(name, BIAS_NAME[int(frames[tf]["bias"].iloc[-1])])
              for name, tf in [("Weekly", "W"), ("Daily", "D"), ("4H", "H4")]]
    weekly = int(frames["W"]["bias"].iloc[-1])
    if weekly == 1:
        plan = "Weekly is BULLISH: prioritize BUY setups at valid demand zones."
    elif weekly == -1:
        plan = "Weekly is BEARISH: prioritize SELL setups at valid supply zones."
    else:
        plan = "Weekly bias is NEUTRAL: no directional setup is authorized."

    zones = analysis.active_zones(frames)
    setups = score(analysis.build_setups(frames, label=False, last_bars=config.LAST_BARS))
    draw_chart(m15, zones, setups)

    structure = [_structure_row("M15", m15), _structure_row("H4", frames["H4"]),
                 _structure_row("D1", frames["D"])]
    atr = float(m15["atr"].iloc[-1]) if pd.notna(m15["atr"].iloc[-1]) else 0.0
    liquidity = detect_liquidity(
        m15, swing=config.LIQUIDITY_SWING,
        tolerance=atr * config.LIQUIDITY_ATR_TOLERANCE,
        lookback=config.LIQUIDITY_LOOKBACK,
    )

    zone_rows = []
    for z in zones.itertuples():
        zone_rows.append({"tf": z.tf, "kind": z.kind, "side": "BUY" if z.direction == 1 else "SELL",
                          "bottom": round(z.bottom, 2), "top": round(z.top, 2),
                          "aligned": bool(z.aligned), "dist": round(z.dist, 2)})
    setup_rows = []
    for s in setups.itertuples():
        setup_rows.append({"time": s.time.strftime("%d %b %H:%M"), "side": s.direction_name,
                           "zone": "%s %s" % (s.tf, s.kind), "entry": round(s.entry, 2),
                           "stop": round(s.stop, 2), "target": round(s.target, 2),
                           "p_win": round(s.p_win * 100), "verdict": s.verdict})

    last_price = float(quote["bid"]) if quote else float(m15["close"].iloc[-1])
    return {
        "note": note, "plan": plan, "biases": biases,
        "price": round(last_price, 2),
        "bid": round(quote["bid"], 2) if quote else None,
        "ask": round(quote["ask"], 2) if quote else None,
        "spread": round(quote["spread"], 3) if quote else None,
        "quote_time": str(quote["tick_time"]) if quote else "Historical CSV",
        "last_candle": m15["avail"].iloc[-1].strftime("%d %b %Y %H:%M"),
        "zones": zone_rows, "setups": setup_rows,
        "structure": structure, "liquidity": liquidity, "data_quality": quality,
        "stats": read_csv_or_empty(config.STATS_FILE).to_dict("records"),
        "metrics": read_csv_or_empty(config.METRICS_FILE).to_dict("records"),
        "rr": config.RR, "last_bars": config.LAST_BARS,
    }
