"""Dashboard and read-only report endpoints. No trading endpoints exist here."""
from datetime import timezone
import json

import pandas as pd
from flask import Blueprint, Response, jsonify, render_template

import config
from .agent import run_analysis

main = Blueprint("main", __name__)
cache = {"time": None, "data": None}


def refresh_cache(force=False):
    now = pd.Timestamp.now(tz="UTC")
    if (force or cache["time"] is None
            or (now - cache["time"]).total_seconds() >= config.REFRESH_SECONDS):
        cache["data"] = run_analysis()
        cache["time"] = now
    return cache["data"]


@main.route("/")
def index():
    try:
        data = refresh_cache()
        return render_template(
            "index.html",
            refresh=config.REFRESH_SECONDS,
            updated=cache["time"].strftime("%Y-%m-%d %H:%M:%S UTC"),
            **data,
        )
    except Exception as exc:
        return render_template("error.html", error=str(exc)), 503


@main.route("/report.json")
def report_json():
    """Download the latest read-only market-analysis snapshot as JSON."""
    try:
        data = refresh_cache()
        payload = {
            "generated_at_utc": cache["time"].isoformat(),
            "symbol": config.MT5_SYMBOL,
            "mode": "ANALYSIS_ONLY_NO_ORDER_EXECUTION",
            "analysis": data,
        }
        return Response(
            json.dumps(payload, indent=2, default=str),
            mimetype="application/json",
            headers={"Content-Disposition": "attachment; filename=gold_analysis_report.json"},
        )
    except Exception as exc:
        return jsonify({"error": str(exc), "mode": "ANALYSIS_ONLY_NO_ORDER_EXECUTION"}), 503


@main.route("/signals.csv")
def signals_csv():
    """Download current detected signals as CSV (empty file with headers if no signal)."""
    try:
        data = refresh_cache()
        columns = ["time", "side", "zone", "entry", "stop", "target", "p_win", "verdict"]
        signals = pd.DataFrame(data.get("setups", []), columns=columns)
        csv_text = signals.to_csv(index=False)
        return Response(
            csv_text,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=gold_signals.csv"},
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 503
