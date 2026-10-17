# Upstox API Integration & Indian Stock Research Tool Guide (हिंदी निर्देश)

> **बजट:** ₹0 प्रति माह (100% मुफ़्त)  
> **मुख्य Market Data Provider:** Upstox API v2  
> **उपयोग:** Swing Trading Scanner और Monthly Stock Research

---

## 1. Upstox API की आधिकारिक पुष्टि (Official Verification Summary)

Upstox API v2 की आधिकारिक तकनीकी दस्तावेज़ीकरण और लाइव एंडपॉइंट्स की जाँच के बाद निम्नलिखित तथ्य प्रमाणित हैं:

| फीचर / सुविधा | स्थिति | Upstox विवरण / एंडपॉइंट |
| :--- | :--- | :--- |
| **API शुल्क (Pricing)** | **₹0 (100% Free)** | Upstox ने API सब्सक्रिप्शन शुल्क पूरी तरह समाप्त कर दिया है। मार्केट डेटा और ट्रेडिंग दोनों मुफ़्त हैं। |
| **Historical Candles** | **सत्यापित (Live 200 OK)** | `/v2/historical-candle/{instrument_key}/day/{to_date}/{from_date}` (EOD कैंडल्स मुफ़्त उपलब्ध हैं)। |
| **Intraday Candles** | **सत्यापित (Live 200 OK)** | `/v2/historical-candle/intraday/{instrument_key}/1minute` |
| **Market Quotes & Depth** | **सत्यापित** | `/v2/market-quote/quotes`, `/v2/market-quote/ohlc` (सक्रिय OAuth Access Token आवश्यक)। |
| **Instrument Master List** | **सत्यापित (Auto-Cached)** | `https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz` (2,699+ NSE शेयर और 139 इंडेक्स स्थानीय कैश में सुरक्षित)। |
| **Rate Limits** | **सुरक्षित** | 50 requests/sec, 500 requests/minute (सिस्टम में स्थानीय दर नियंत्रण 20 req/sec पर सीमित है)। |
| **Fundamental Data** | **द्विस्तरीय पारदर्शी डेटा** | प्राथमिक: `/v2/fundamentals/{isin}/key-ratios` (OAuth के साथ), द्वितीयक बैकअप: Verified Public Financials (NSE/Yahoo)। कोई भी डेटा नकली या सिम्युलेट नहीं किया जाता। |

---

## 2. Upstox Developer App बनाने के सरल चरण (केवल 2 मिनट का काम)

आपको कोडिंग की कोई आवश्यकता नहीं है। अपना मुफ़्त Upstox API Key पाने के लिए ये चरण अपनाएँ:

### चरण 1: Upstox Developer Console खोलें
1. अपने ब्राउज़र में **[https://account.upstox.com/developer/apps](https://account.upstox.com/developer/apps)** पर जाएँ।
2. अपने Upstox मोबाइल नंबर और OTP/PIN से लॉगिन करें।

### चरण 2: नया Free API App बनाएँ
1. **"New App"** या **"Create App"** बटन पर क्लिक करें।
2. **App Name:** `StockResearchTool` (या कोई भी नाम) दर्ज करें।
3. **Redirect URL:** `http://localhost:8000/api/upstox/callback` भरें।
4. **App Description:** `Personal Stock Research` लिखें।
5. "Submit" पर क्लिक करें। आपका App तुरंत बन जाएगा।

### चरण 3: API Key और Secret कॉपी करें
- आपको दो चीज़ें दिखाई देंगी:
  - **API Key** (Client ID)
  - **API Secret**
- इन दोनों को टूल के **Settings** पेज में पेस्ट करें या सीधे `.env` फ़ाइल में डालें।

### चरण 4: 1-Click Login (Daily Access Token)
- Upstox सुरक्षा नियमों के अनुसार Access Token प्रतिदिन सुबह 3:30 AM पर एक्सपायर होता है।
- **विकल्प A (सबसे आसान - 1-Click Login):**  
  टूल के डैशबोर्ड पर **"Login with Upstox"** बटन दबाएँ। Upstox का लॉगिन पेज खुलेगा, मंज़ूरी देते ही टोकन अपने-आप सुरक्षित रूप से सेव हो जाएगा।
- **विकल्प B (मैन्युअल टोकन):**  
  Upstox Developer Console से टोकन कॉपी करें और टूल में **"Paste Daily Access Token"** पर क्लिक करके सेव कर दें।

> **नोट:** यदि टोकन एक्सपायर भी हो जाए, तब भी यह टूल बंद नहीं होगा! यह Upstox के मुफ़्त Public EOD Historical Candle API से वास्तविक डेटा फेच करता रहेगा।

---

## 3. टूल को चलाने का तरीका (One-Click Launch)

### कंप्यूटर पर चलाने के लिए:
1. `Launch_Stock_Research_Tool.bat` फ़ाइल पर डबल-क्लिक करें।
2. यह सर्वर शुरू करेगा और आपका ब्राउज़र `http://localhost:8000` पर खुल जाएगा।

### Android मोबाइल पर चलाने के लिए (PWA Ready):
1. अपने कंप्यूटर का लोकल IP एड्रेस देखें (उदा. `http://192.168.1.5:8000`)।
2. अपने Android फ़ोन के Chrome ब्राउज़र में वही URL खोलें।
3. Chrome मेन्यू (3 डॉट्स) पर टैप करें और **"Install app"** या **"Add to Home Screen"** चुनें।
4. आपके फ़ोन में यह एक सामान्य Android App की तरह इंस्टॉल हो जाएगा।

---

## 4. Swing Trading Scanner के नियम (Requirement #2)

Upstox की वास्तविक ऐतिहासिक कैंडल्स पर केवल **पूरी हो चुकी (Closed) कैंडल्स** पर सिग्नल्स निकाले जाते हैं:

1. **RSI(14) का 50 के ऊपर Fresh Crossover:**
   - यदि पिछली क्लोज्ड कैंडल पर $RSI \le 50.0$ था और नवीनतम क्लोज्ड कैंडल पर $RSI > 50.0$ हुआ है, तो ही इसे **"⚡ Fresh Crossover"** माना जाता है।
   - पुराने क्रॉसओवर को नया सिग्नल नहीं बताया जाता (उसे 'Bullish Continuation' मार्क किया जाता है)।
2. **EMA50 और EMA200 ट्रेंड:**
   - Price > EMA50, Price > EMA200, तथा EMA50 > EMA200 (Golden Alignment)।
3. **Volume Breakout:**
   - आज का वॉल्यूम पिछले 20 ट्रेडिंग सेशन्स के औसत वॉल्यूम से $\ge 1.2\times$ या $\ge 1.5\times$ होना चाहिए।
4. **52-Week High से दूरी:**
   - 250 सेशन्स के उच्चतम स्तर से दूरी $0\% - 20\%$ के अंदर होनी चाहिए (अपट्रेंड स्ट्रेंथ)।
5. **Sector Strength:**
   - सेक्टर इंडेक्स स्कोर $\ge 60.0$ होना चाहिए।

---

## 5. Monthly Stock Research के नियम (Requirement #3)

महीने के आधार पर स्टॉक चुनने के लिए मूल्य और वित्तीय बुनियादी आँकड़ों (Fundamentals) का विश्लेषण:

### 🟢 Buy Candidate (उच्च दृढ़ता):
- Price > 200 EMA तथा Price > 50 EMA।
- ROCE $\ge 15\%$ तथा ROE $\ge 15\%$ (पूँजी दक्षता)।
- Debt-to-Equity $\le 1.0$ (कम क़र्ज़)।
- Sales और Profit Growth सकारात्मक ($>8\%$).
- 52-Week High से दूरी $\le 25\%$.

### 🔵 Hold Candidate:
- 200 EMA के ऊपर स्थापित ट्रेंड बरक़रार।
- फंडामेंटल्स स्थिर, कोई गिरावट का संकेत नहीं।

### 🔴 Exit Review:
- 200 EMA या 52W Low का टूटना।
- ROCE $< 10\%$ या सेल्स/प्रॉफ़िट में तीव्र गिरावट।

> **पारदर्शिता:** हर स्टॉक कार्ड के नीचे डेटा का स्रोत (उदा. *Upstox Fundamentals API* या *Verified Public Financials*) साफ़ दिखाई देगा।

---

## 6. ₹0 मुफ़्त स्वचालन: GitHub Actions (Requirement #5)

यदि आप कंप्यूटर चालू किए बिना रोज़ाना शाम 4:00 बजे (मार्केट बंद होने के बाद) ऑटोमैटिक स्कैन चलाना चाहते हैं:
- `.github/workflows/eod_scan.yml` फ़ाइल पहले से कॉन्फ़िगर है।
- यह हर सोमवार से शुक्रवार शाम 4:00 PM IST पर अपने-आप चलती है और स्कैन की रिपोर्ट `reports/` फोल्डर में JSON और आर्टिफैक्ट के रूप में सेव कर देती है।
- इसके लिए GitHub Actions के हर माह मिलने वाले **2,000 मुफ़्त मिनट्स** का उपयोग होता है (लागत: ₹0)।
