"""
Local Runner for Swing Delivery Trade Screener.
Run with: python run.py
Open: http://localhost:5000
"""

import sys
import os

# Ensure api directory is found
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "api"))

from index import app

if __name__ == "__main__":
    print("====================================================")
    print("🎯 Swing Delivery Trade Screener (Nifty 100)")
    print("🚀 Starting local server at http://127.0.0.1:5000")
    print("====================================================")
    app.run(host="127.0.0.1", port=5000, debug=True)
