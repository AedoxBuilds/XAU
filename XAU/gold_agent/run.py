"""Start the local analysis dashboard. This app has no trade execution code."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Localhost only: do not expose the MT5-connected dashboard to the public internet.
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
