# ============================================================
# analysis.py  -  ALL strategy logic (used by training AND live)
#   weekly bias -> D / 4H zones (OB, FVG) -> 15m confirmation
# Times are in the timezone of your data (days/weeks follow it).
# ============================================================
import numpy as np
import pandas as pd
import config

TF_SPAN = {"W": pd.Timedelta(days=7), "D": pd.Timedelta(days=1),
           "H4": pd.Timedelta(hours=4), "M15": pd.Timedelta(minutes=15)}
TF_RULE = {"W": "W-SUN", "D": "1D", "H4": "4h", "M15": "15min"}
ZONE_COLS = ["tf", "kind", "direction", "bottom", "top", "avail"]


# ---------------- loading / resampling ----------------
def load_csv(path):
    """Any CSV with datetime, open, high, low, close columns."""
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    for name in ["datetime", "date", "time", "timestamp", "gmt time", "local time"]:
        if name in df.columns:
            df = df.rename(columns={name: "datetime"})
            break
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_localize(None)
    df = df.set_index("datetime").sort_index()
    df = df[~df.index.duplicated()]
    return df[["open", "high", "low", "close"]].astype(float).dropna()


def resample_ohlc(df, tf):
    out = df.resample(TF_RULE[tf], closed="left", label="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    out["avail"] = out.index + TF_SPAN[tf]      # time the candle is CLOSED
    return out


def make_frames(m15):
    """Build Weekly, Daily, 4H and 15m candles from one 15m dataframe."""
    return {tf: resample_ohlc(m15, tf) for tf in ["W", "D", "H4", "M15"]}


# ---------------- indicators ----------------
def add_atr(df, n=config.ATR_PERIOD):
    prev = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - prev).abs(),
                    (df["low"] - prev).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(n).mean()
    return df


def add_bias(df, n):
    """Market structure bias: +1 bullish (HH+HL), -1 bearish (LH+LL), 0 neutral.
    A swing is only used n candles AFTER it formed (no look-ahead)."""
    hi = df["high"].rolling(2 * n + 1, center=True).max()
    lo = df["low"].rolling(2 * n + 1, center=True).min()
    sh = df["high"].where(df["high"] == hi).shift(n).dropna()
    sl = df["low"].where(df["low"] == lo).shift(n).dropna()
    cur_h = sh.reindex(df.index).ffill()
    prev_h = sh.shift(1).reindex(df.index).ffill()
    cur_l = sl.reindex(df.index).ffill()
    prev_l = sl.shift(1).reindex(df.index).ffill()
    up = (cur_h > prev_h).astype(int) + (cur_l > prev_l).astype(int)
    down = (cur_h < prev_h).astype(int) + (cur_l < prev_l).astype(int)
    df["bias"] = np.sign(up - down).astype(int)
    return df


def prep_frames(frames):
    out = {}
    for tf, f in frames.items():
        f = f.copy()
        add_atr(f)
        if tf != "M15":
            add_bias(f, config.SWING_N[tf])
        out[tf] = f
    return out


def bias_array(m15, htf):
    """Bias of the last CLOSED higher-timeframe candle, for every 15m candle."""
    pos = np.searchsorted(htf["avail"].values, m15["avail"].values, side="right") - 1
    vals = htf["bias"].values
    return np.where(pos >= 0, vals[np.clip(pos, 0, None)], 0)


# ---------------- zones: FVG + order blocks ----------------
def find_zones(df, tf):
    o, h, l, c = (df[x].values for x in ["open", "high", "low", "close"])
    atr, avail = df["atr"].values, df["avail"].values
    rows = []
    for i in range(2, len(df)):
        a = atr[i]
        if np.isnan(a):
            continue
        # Fair Value Gap (3-candle gap, known when candle i closes)
        if l[i] > h[i - 2] and (l[i] - h[i - 2]) >= config.MIN_FVG_ATR * a:
            rows.append((tf, "FVG", 1, h[i - 2], l[i], avail[i]))
        if h[i] < l[i - 2] and (l[i - 2] - h[i]) >= config.MIN_FVG_ATR * a:
            rows.append((tf, "FVG", -1, h[i], l[i - 2], avail[i]))
        # Order block: last opposite candle before a strong displacement candle
        if abs(c[i] - o[i]) >= config.OB_DISPLACEMENT * a:
            if c[i] > o[i] and o[i - 1] > c[i - 1] and c[i] > h[i - 1]:
                rows.append((tf, "OB", 1, l[i - 1], h[i - 1], avail[i]))
            if c[i] < o[i] and o[i - 1] < c[i - 1] and c[i] < l[i - 1]:
                rows.append((tf, "OB", -1, l[i - 1], h[i - 1], avail[i]))
    if not rows:
        return pd.DataFrame(columns=ZONE_COLS + ["expiry"])
    z = pd.DataFrame(rows, columns=ZONE_COLS)
    z["expiry"] = z["avail"] + config.ZONE_MAX_AGE[tf] * TF_SPAN[tf]
    return z


def all_zones(frames):
    z = [find_zones(frames["D"], "D"), find_zones(frames["H4"], "H4")]
    z = [x for x in z if len(x)]
    if not z:
        return pd.DataFrame(columns=ZONE_COLS + ["expiry"])
    return pd.concat(z, ignore_index=True)


def active_zones(frames):
    """Zones that are still valid right now (not expired, not broken)."""
    m15 = frames["M15"]
    now, price = m15["avail"].iloc[-1], m15["close"].iloc[-1]
    zs = all_zones(frames)
    if zs.empty:
        return zs
    zs = zs[(zs["avail"] >= m15.index[0]) & (zs["avail"] <= now) & (zs["expiry"] > now)]
    idx, cl = m15.index.values, m15["close"].values
    keep = []
    for z in zs.itertuples():
        s = np.searchsorted(idx, z.avail.to_datetime64())
        broken = (cl[s:] < z.bottom).any() if z.direction == 1 else (cl[s:] > z.top).any()
        keep.append(not broken)
    zs = zs[keep].copy()
    if zs.empty:
        return zs
    zs["dist"] = np.where((price >= zs["bottom"]) & (price <= zs["top"]), 0.0,
                          np.minimum((price - zs["bottom"]).abs(), (price - zs["top"]).abs()))
    weekly = int(frames["W"]["bias"].iloc[-1])
    zs["aligned"] = zs["direction"] == weekly
    return zs.sort_values("dist").head(8).reset_index(drop=True)


# ---------------- setups (15m confirmation) ----------------
def _first(a):
    return int(np.argmax(a)) if a.any() else len(a)


def session_of(hour):
    if 0 <= hour < 7:
        return 1, "Asia"
    if 7 <= hour < 12:
        return 2, "London"
    if 12 <= hour < 21:
        return 3, "New York"
    return 0, "Off-hours"


def build_setups(frames, label=True, last_bars=None):
    """Find every setup. label=True also checks the result (for training).
    last_bars=N keeps only setups that happened in the last N candles (live)."""
    m15 = frames["M15"]
    idx = m15.index.values
    o, h, l, c = (m15[x].values for x in ["open", "high", "low", "close"])
    atr, avail = m15["atr"].values, m15["avail"].values
    bW, bD, bH = (bias_array(m15, frames[t]) for t in ["W", "D", "H4"])

    zones = all_zones(frames)
    if zones.empty:
        return pd.DataFrame()
    zones = zones[zones["avail"] >= m15.index[0]].sort_values("avail").reset_index(drop=True)
    z_dir, z_bot, z_top = zones["direction"].values, zones["bottom"].values, zones["top"].values
    z_av, z_ex = zones["avail"].values, zones["expiry"].values

    rows = []
    for k in range(len(zones)):
        d, bot, top = z_dir[k], z_bot[k], z_top[k]
        start = np.searchsorted(idx, z_av[k], side="left")
        end = np.searchsorted(idx, z_ex[k], side="left")
        if end - start < 2:
            continue
        s = slice(start, end)
        if d == 1:
            touch = l[s] <= top
            confirm = (c[s] > o[s]) & (c[s] > bot)
            broken = c[s] < bot
        else:
            touch = h[s] >= bot
            confirm = (c[s] < o[s]) & (c[s] < top)
            broken = c[s] > top
        ok = (bW[s] == d) & ~np.isnan(atr[s])         # weekly bias must agree
        hits = np.flatnonzero(touch & confirm & ok)
        if len(hits) == 0:
            continue
        j = hits[0]
        if broken[:j].any():
            continue
        i = start + j
        if last_bars and i < len(c) - last_bars:
            continue
        entry = c[i]
        buf = config.SL_BUFFER_ATR * atr[i]
        stop = (min(l[i], bot) - buf) if d == 1 else (max(h[i], top) + buf)
        risk = abs(entry - stop)
        if risk < config.MIN_RISK_ATR * atr[i] or risk > config.MAX_RISK_ATR * atr[i]:
            continue
        target = entry + d * config.RR * risk

        win, r = np.nan, np.nan
        if label:
            a, b = i + 1, min(i + 1 + config.MAX_HOLD_BARS, len(c))
            sl_hit = (l[a:b] <= stop) if d == 1 else (h[a:b] >= stop)
            tp_hit = (h[a:b] >= target) if d == 1 else (l[a:b] <= target)
            si, ti = _first(sl_hit), _first(tp_hit)
            if si == len(sl_hit) and ti == len(tp_hit):      # nothing hit
                if b - a < config.MAX_HOLD_BARS:
                    continue                                  # not enough data to know
                win, r = 0, d * (c[b - 1] - entry) / risk
            elif ti < si:
                win, r = 1, config.RR
            else:                                             # SL first (or same candle)
                win, r = 0, -1.0

        t_close = pd.Timestamp(avail[i])
        sess, sess_name = session_of(t_close.hour)
        overlap = ((z_dir == d) & (z_av <= avail[i]) & (z_ex > avail[i])
                   & (z_bot <= top) & (z_top >= bot))
        rows.append({
            "time": t_close, "direction": int(d),
            "direction_name": "BUY" if d == 1 else "SELL",
            "kind": zones["kind"].iloc[k], "tf": zones["tf"].iloc[k],
            "zone_bottom": bot, "zone_top": top,
            "entry": entry, "stop": stop, "target": target, "atr": atr[i],
            "kind_ob": int(zones["kind"].iloc[k] == "OB"),
            "tf_daily": int(zones["tf"].iloc[k] == "D"),
            "d_rel": int(bD[i] * d), "h4_rel": int(bH[i] * d),
            "zone_size_atr": (top - bot) / atr[i], "risk_atr": risk / atr[i],
            "hour": t_close.hour, "session": sess, "session_name": sess_name,
            "dow": t_close.dayofweek, "confluence": int(overlap.sum()) - 1,
            "prior_touches": int(touch[:j].sum()),
            "zone_age_hours": (avail[i] - z_av[k]) / np.timedelta64(1, "h"),
            "win": win, "r": r,
        })
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows).sort_values("time")
    out = out.drop_duplicates(["time", "direction"]).reset_index(drop=True)
    return out


# ---------------- quant statistics ----------------
def _stats(g):
    r = g["r"].values
    eq = np.cumsum(r)
    drawdown = (np.maximum.accumulate(eq) - eq).max() if len(r) else 0
    streak = best = 0
    for x in r:
        streak = streak + 1 if x < 0 else 0
        best = max(best, streak)
    return {"trades": len(r), "win_rate_%": (g["win"] == 1).mean() * 100,
            "expectancy_R": r.mean(), "total_R": r.sum(),
            "max_drawdown_R": drawdown, "max_losing_streak": best}


def quant_table(setups):
    setups = setups.sort_values("time")
    groups = [("ALL setups", setups)]
    for col, name in [("session_name", "session"), ("kind", "type"),
                      ("tf", "zone TF"), ("direction_name", "side")]:
        for val, g in setups.groupby(col):
            groups.append((f"{name}: {val}", g))
    return pd.DataFrame([{"group": n, **_stats(g)} for n, g in groups])
