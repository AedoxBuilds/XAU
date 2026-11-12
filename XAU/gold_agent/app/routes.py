from flask import Blueprint, render_template
import pandas as pd
import config
from .agent import run_analysis

main = Blueprint("main", __name__)
cache = {"time": None, "data": None}


@main.route("/")
def index():
    try:
        now = pd.Timestamp.now()
        if cache["time"] is None or (now - cache["time"]).total_seconds() > config.REFRESH_SECONDS - 5:
            cache["data"] = run_analysis()
            cache["time"] = now
        return render_template("index.html", refresh=config.REFRESH_SECONDS,
                               updated=cache["time"].strftime("%H:%M:%S"), **cache["data"])
    except Exception as e:
        return render_template("error.html", error=str(e))
