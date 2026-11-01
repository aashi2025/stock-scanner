# 🎯 Indian Stocks Swing Trading Action Screener (Nifty 100)

Automated End-of-Day (EOD) swing trading action screener for Indian equities (Nifty 50 and Nifty Next 50).
Calculates exact Entry, Stop Loss (SL), Target (1:2 R:R), and Signal (`🟢 READY TO BUY` / `⏳ WAIT FOR CONFIRMATION`).

## 📊 Core Screening Rules:
1. **Primary Trend:** Daily Close > 200 EMA and Supertrend (7, 3) Bullish.
2. **Setup Structure:** 
   - **Setup A:** 200 EMA / Supertrend support pullback with green reversal candle.
   - **Setup B:** Solid breakout above 20-day swing resistance without large upper rejection wick.
3. **Momentum Filter:** Daily RSI(14) between 50.0 and 68.0.
4. **Auto Levels:** Entry at CMP/Breakout, Stop Loss below swing low (2–5% risk), Target at minimum 1:2 Risk-to-Reward ratio.

---

## 🚀 How to Run Locally

```bash
# 1. Navigate to the screener_web folder
cd screener_web

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the application
python run.py
```
Open your browser at: **`http://localhost:5000`**

---

## ☁️ How to Deploy to Vercel (100% Free Serverless)

This project is pre-configured with `vercel.json` and `api/index.py`:

```bash
# Install Vercel CLI (if not already installed)
npm i -g vercel

# Deploy directly
vercel
```
Or import this Git repository directly into your [Vercel Dashboard](https://vercel.com/new).
