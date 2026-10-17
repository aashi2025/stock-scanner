# 🇮🇳 Indian Stock Research Platform — Zero Budget MVP (Phase 1 & Phase 2)

एक 100% मुफ़्त, पारदर्शी और नियम-आधारित (Rule-Based) भारतीय शेयर बाज़ार (NSE) रिसर्च टूल। इसमें कोई भी सशुल्क (Paid) API या मासिक सब्सक्रिप्शन नहीं है — इसका मासिक ख़र्च **₹0** है।

---

## 🎯 मुख्य उद्देश्य (Objective)

यह टूल नए निवेशकों और स्विंग ट्रेडर्स को बिना किसी कोडिंग ज्ञान के निम्नलिखित सुविधाएँ देता है:
1. **फ्रेश स्विंग सिग्नल्स (Fresh Swing Signals):** केवल ताज़ा RSI(14) क्रॉसओवर (जो पिछली कैंडल पर $\le 50$ था और ताज़ा क्लोजिंग पर $> 50$ हुआ) और 50/200 EMA एलाइनमेंट।
2. **मल्टी-टाइमफ्रेम कन्फर्मेशन (Phase 2 MTF):** साप्ताहिक (Weekly 20 EMA + Weekly RSI) ट्रेंड के साथ डबल कन्फर्मेशन।
3. **स्मार्ट मनी एक्युमुलेशन ट्रैकर (Phase 2 Delivery & Institutional Tracker):** Close Location Value (CLV) और On-Balance Volume (OBV) से संस्थागत खरीद की पहचान।
4. **पोर्टफोलियो बैकटेस्टिंग (Phase 2 Multi-Stock Portfolio Simulation):** पूरे पोर्टफोलियो (₹5,00,000) पर एक साथ 5 पोजीशन, कैश मैनेजमेंट, भारतीय टैक्स (STT 0.1%, Stamp Duty, Turnover Fees, GST), Sharpe और Sortino रेश्यो।
5. **इंटरएक्टिव कैंडलस्टिक चार्ट्स (Phase 2 Plotly Charts):** ज़ूम, पैन, EMA लाइन्स, और टारगेट/स्टॉप-लॉस लेवल्स के साथ।
6. **पर्सनल वॉचलिस्ट व इनवैलिडेशन अलर्ट्स (Phase 2 Watchlist):** 50 EMA ब्रेकडाउन या मोमेंटम ख़त्म होने पर तुरंत चेतावनी।
7. **ज़ीरो-कॉस्ट टेलीग्राम अलर्ट्स (Phase 2 Alerts):** बाज़ार बंद होने के बाद मुफ़्त में मोबाइल पर अलर्ट्स।

---

## 🏗️ सिस्टम आर्किटेक्चर (System Architecture)

```
[ Local Daily OHLCV CSV / Free Yahoo Feed ]
                     │
                     ▼
       ┌───────────────────────────┐
       │     Data Validator Gate   │  ◄── (Schema, NaNs, High < Low, Stale Checks)
       └─────────────┬─────────────┘
                     │ (Verified Data Only)
                     ▼
       ┌───────────────────────────┐
       │   Technical & Indicator   │  ◄── (EMA 50/200, RSI 14, ATR, 52W High)
       │        Engine             │
       └─────────────┬─────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌──────────────────┐   ┌───────────────────────┐
│  Swing Scanner   │   │  Monthly Research     │
│ (Fresh Cross >50)│   │  (ROCE, ROE, D/E)     │
└────────┬─────────┘   └──────────┬────────────┘
         │                        │
         └───────────┬────────────┘
                     ▼
       ┌───────────────────────────┐
       │ 5-Dimension Ranking Model │  ◄── (Trend, Mom, Quality, Valuation, Risk)
       └─────────────┬─────────────┘
                     │
         ┌───────────┴───────────────────────┐
         ▼                                   ▼
┌─────────────────────────────────┐   ┌───────────────────────┐
│ Streamlit Interactive UI        │   │ Daily EOD Markdown,   │
│ (7 Active Tabs + Plotly Charts) │   │ JSON & Telegram Alert │
└─────────────────────────────────┘   └───────────────────────┘
```

---

## 📋 7 मुख्य डैशबोर्ड टैब्स (Dashboard Tabs)

1. **Market Overview (बाज़ार स्थिति):** निफ्टी 50 का रिजीम (Bullish/Bearish), 50 व 200 EMA लेवल्स, और सेक्टोरल स्ट्रेंथ टेबल।
2. **Fresh Swing Signals (ताज़ा स्विंग सिग्नल्स):** केवल ताज़ा सिग्नल्स, साप्ताहिक MTF स्टेटस, स्टॉप लॉस और टारगेट (1:2 और 1:3 रिस्क-रिवॉर्ड)।
3. **Monthly Candidates (मासिक रिसर्च):** Buy, Hold, और Exit Reviews।
4. **Stock Details & Chart (विस्तृत विश्लेषण व कैंडलस्टिक चार्ट):** Plotly इंटरएक्टिव चार्ट, 50/200 EMA, RSI सबप्लॉट, और स्मार्ट मनी एक्युमुलेशन।
5. **Portfolio & Single Backtest (बैकटेस्टिंग इंजन):** मल्टी-स्टॉक पोर्टफोलियो सिमुलेशन, Sharpe Ratio, Sortino Ratio, मैक्सिमम ड्रॉडाउन, और इक्विटी कर्व।
6. **Watchlist & Alerts (निजी वॉचलिस्ट):** सेव किए गए स्टॉक्स की इनवैलिडेशन मॉनिटरिंग।
7. **Data Health (डेटा स्वास्थ्य):** वेरिफाइड, पुराना (Stale) डेटा स्टेटस + नई CSV फ़ाइल ड्रैग-एंड-ड्रॉप अपलोडर।

---

## ⚡ त्वरित शुरुआत निर्देश (Beginner Quickstart)

### तरीका 1: एक क्लिक में शुरू करें (Windows 1-Click Launch)
फ़ोल्डर में दिए गए **`Launch_Stock_Research_Tool.bat`** फ़ाइल पर डबल-क्लिक करें। यह सीधे `http://localhost:8501` पर डैशबोर्ड खोल देगा।

---

### तरीका 2: टर्मिनल / PowerShell से चलाना

1. **स्टॉक स्कैनर डायरेक्टरी में आएँ:**
   ```powershell
   cd C:\Users\Lenovo\.gemini\antigravity\scratch\stock_scanner
   ```

2. **सभी 25 यूनिट टेस्ट चलाकर वेरिफ़ाई करें:**
   ```powershell
   python -m pytest tests/ -v
   ```

3. **डेली रिपोर्ट और टेलीग्राम अलर्ट बनाएं:**
   ```powershell
   python generate_daily_report.py
   ```

4. **Streamlit डैशबोर्ड शुरू करें:**
   ```powershell
   python -m streamlit run streamlit_app.py
   ```
   ब्राउज़र में खोलें: `http://localhost:8501`

---

## 🧪 यूनिट टेस्ट्स (All 25 Unit Tests Passing)

- `test_backtest.py`: भारतीय टैक्स और बैकटेस्ट संरचना।
- `test_data_validation.py`: डेटा स्कीमा, डुप्लीकेट और अमान्य डेटा रिजेक्शन।
- `test_delivery_tracker.py`: On-Balance Volume (OBV) और स्मार्ट मनी एक्युमुलेशन।
- `test_indicators.py`: EMA, RSI और ताज़ा क्रॉसओवर।
- `test_multi_timeframe.py`: साप्ताहिक रीसॅम्पलिंग और MTF कन्फर्मेशन।
- `test_portfolio_backtest.py`: मल्टी-स्टॉक पोर्टफोलियो और पूंजी प्रबंधन।
- `test_ranking.py`: 5-डाइमेंशनल स्कोरिंग।
- `test_synthetic_scan.py`: सिंथेटिक टेस्ट डेटा पर ताज़ा बनाम बासी सिग्नल्स।
- `test_watchlist.py`: वॉचलिस्ट जोड़ना और हटाना।

---

## ⚠️ अस्वीकरण (Research Disclaimer)

*सभी स्कोर्स और लेवल्स केवल सांख्यिकीय और गणितीय नियम-आधारित अध्ययन (Research Heuristics) हैं। यह वित्तीय सलाह या लाभ की गारंटी नहीं है। कोई भी वास्तविक ट्रेड लेने से पहले अपने SEBI-पंजीकृत वित्तीय सलाहकार से परामर्श अवश्य लें।*
