# 🌐 क्लाउड डिप्लॉयमेंट गाइड — Vercel & Streamlit Cloud (100% Free / ₹0 बजट)

यह गाइड उनके लिए है जिनका कोई कोडिंग बैकग्राउंड नहीं है और जो चाहते हैं कि उनका **Indian Stock Research Tool** 24 घंटे ऑनलाइन लाइव चले, ताकि **कंप्यूटर बंद होने के बाद भी यह कभी बंद न हो** और मोबाइल या किसी भी डिवाइस से 24/7 खोला जा सके।

---

## 1. कंप्यूटर पर बंद क्यों हो जाता था?
जब आप अपने कंप्यूटर पर `Launch_Stock_Research_Tool.bat` या `localhost:8501` चलाते हैं, तो आपका पर्सनल कंप्यूटर ही सर्वर की तरह काम कर रहा होता है। 
- जैसे ही आप टर्मिनल (Black window) बंद करते हैं या लैपटॉप शटडाउन करते हैं, यह लोकल सर्वर बंद हो जाता है।
- **समाधान:** इसे इंटरनेट के फ्री क्लाउड सर्वर (Vercel या Streamlit Cloud) पर डाल देना। वहां यह 24 घंटे, 365 दिन अपने आप चलता रहेगा!

---

## 2. आपके पास 2 मुफ़्त (₹0) विकल्प हैं:

| फ़ीचर | विकल्प A: Streamlit Cloud | विकल्प B: Vercel |
|---|---|---|
| **वेबसाइट लिंक** | `https://your-app.streamlit.app` | `https://your-app.vercel.app` |
| **इंटरफ़ेस** | 7-टैब वाला पूरा Streamlit डैशबोर्ड | मॉडर्न Tailwind + PWA वेब ऐप |
| **लागत (Cost)** | ₹0 / मुफ़्त (Life-time) | ₹0 / मुफ़्त (Life-time) |
| **सेटअप समय** | सिर्फ 2 मिनट | सिर्फ 2 मिनट |
| **24/7 लाइव** | ✅ हाँ (कंप्यूटर बंद होने पर भी) | ✅ हाँ (कंप्यूटर बंद होने पर भी) |

---

## 3. स्टेप-बाय-स्टेप डिप्लॉयमेंट (Step-by-Step Instructions)

### 📌 Step 1: GitHub पर कोड अपलोड करें (सिर्फ 1 मिनट)
1. अपने ब्राउज़र में [https://github.com](https://github.com) खोलें और लॉगिन करें (अगर अकाउंट नहीं है तो 1 मिनट में फ्री साइनअप करें)।
2. ऊपर दाएँ कोने में **`+`** आइकन दबाकर **"New repository"** चुनें।
3. **Repository name** में लिखें: `stock-scanner`
4. इसे **Public** या **Private** अपनी पसंद से रखें और नीचे हरा बटन **"Create repository"** दबाएं।
5. नए पेज पर आपको नीले रंग का लिंक दिखेगा: **"uploading an existing file"** — इस पर क्लिक करें।
6. आपके प्रोजेक्ट फोल्डर (`stock_scanner`) के अंदर बनी **`stock_scanner_deploy.zip`** को अनज़िप (Extract) करके उसकी सारी फाइलों को ड्रैग करके GitHub के डिब्बे में छोड़ दें।
7. नीचे हरा बटन **"Commit changes"** दबा दें। आपका पूरा प्रोजेक्ट GitHub पर आ गया!

---

### 🚀 Step 2A: Vercel पर लाइव करना (Option A: Vercel Deployment)
1. ब्राउज़र में [https://vercel.com](https://vercel.com) खोलें और **"Continue with GitHub"** चुनकर लॉगिन करें।
2. डैशबोर्ड पर **"Add New..."** ➡️ **"Project"** पर क्लिक करें।
3. आपकी GitHub लिस्ट में से `stock-scanner` के सामने **"Import"** बटन दबाएं।
4. **"Environment Variables"** सेक्शन खोलें और नीचे दी गई 3 कीज़ जोड़ें:
   - `UPSTOX_API_KEY`: *(अपनी Upstox API Key डालें)*
   - `UPSTOX_API_SECRET`: *(अपनी Upstox Secret डालें)*
   - `UPSTOX_ACCESS_TOKEN`: *(अपना Daily Access Token डालें)*
5. नीचे नीला बटन **"Deploy"** दबाएं!
6. **1 मिनट में आपका ऐप तैयार हो जाएगा!** Vercel आपको एक लाइव लिंक देगा जैसे:
   👉 `https://stock-scanner.vercel.app`
   इसे आप अपने मोबाइल में बुकमार्क कर सकते हैं। यह 24 घंटे बिना रुकावट चलता रहेगा!

---

### 🚀 Step 2B: Streamlit Community Cloud पर लाइव करना (Option B: Streamlit Cloud)
अगर आप 7-टैब वाला Streamlit डैशबोर्ड ही ऑनलाइन चलाना चाहते हैं:
1. ब्राउज़र में [https://share.streamlit.io](https://share.streamlit.io) खोलें।
2. **"Continue with GitHub"** पर क्लिक करें।
3. **"Create app"** बटन दबाएं।
4. सेटिंग्स में:
   - **Repository:** `your-username/stock-scanner`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
5. **"Advanced settings"** ➡️ **"Secrets"** में जाकर अपनी `.env` की वैल्यू पेस्ट कर दें:
   ```toml
   UPSTOX_API_KEY = "your_key_here"
   UPSTOX_API_SECRET = "your_secret_here"
   UPSTOX_ACCESS_TOKEN = "your_token_here"
   ```
6. **"Deploy!"** दबाएं।
7. 1 मिनट में आपकी वेबसाइट लाइव हो जाएगी:
   👉 `https://stock-scanner.streamlit.app`

---

## 4. क्या कंप्यूटर बंद करने पर यह बंद होगा?
**बिल्कुल नहीं!**
Vercel और Streamlit Cloud दोनों क्लाउड सर्वर्स पर चलते हैं। आप अपना कंप्यूटर बंद रखें, सो जाएं, या यात्रा कर रहे हों — आप अपने मोबाइल फोन पर कभी भी लिंक खोलकर लाइव मार्केट डेटा, स्विंग सिग्नल्स और बैकटेस्ट देख सकेंगे।
