"""
Flask Serverless Entrypoint for Indian Stocks Swing Trading Action Screener.
Compatible with Vercel Serverless Functions and local Python environment.
"""

import os
import sys
from datetime import datetime
from flask import Flask, render_template, jsonify, request

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from screener_engine import execute_market_scan, NIFTY_100_SYMBOLS

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates"),
    static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
)

# In-memory scan cache
_SCAN_CACHE = {
    "timestamp": None,
    "results": []
}


@app.route("/")
def home():
    """Serves the single-page dark-themed dashboard."""
    return render_template("index.html", total_symbols=len(NIFTY_100_SYMBOLS))


@app.route("/api/scan", methods=["GET", "POST"])
def scan_api():
    """
    Triggers market scan across Nifty 100 universe.
    Returns JSON of filtered setups with entry, target, SL, R:R, and RSI.
    """
    force = request.args.get("force", "false").lower() == "true"
    
    # Simple cache check (5 minutes)
    now = datetime.now()
    if not force and _SCAN_CACHE["timestamp"] and (now - _SCAN_CACHE["timestamp"]).total_seconds() < 300:
        return jsonify({
            "status": "success",
            "cached": True,
            "scan_time": _SCAN_CACHE["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
            "total_scanned": len(NIFTY_100_SYMBOLS),
            "total_matches": len(_SCAN_CACHE["results"]),
            "data": _SCAN_CACHE["results"]
        })

    try:
        results = execute_market_scan()
        _SCAN_CACHE["timestamp"] = now
        _SCAN_CACHE["results"] = results
        
        return jsonify({
            "status": "success",
            "cached": False,
            "scan_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "total_scanned": len(NIFTY_100_SYMBOLS),
            "total_matches": len(results),
            "data": results
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "service": "Swing Action Screener"})


# Required for Vercel Serverless
app_wsgi = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
