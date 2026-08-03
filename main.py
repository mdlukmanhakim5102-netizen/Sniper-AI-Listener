import os
import requests
import uvicorn
from fastapi import FastAPI, Request
from google import genai

app = FastAPI()

# Environment Variables from Render
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Gemini Client Init
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Gemini Client Init Failed: {e}")

def send_telegram_message(message: str):
    """টেলিগ্রাম বটে মেসেজ পাঠানোর সঠিক ফাংশন"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram Credentials Missing!")
        return None

    # টোকেনের ভুল ফরম্যাট ঠিক করার ফিল্টার
    token = TELEGRAM_BOT_TOKEN.strip()
    if token.startswith("bot"):
        token = token[3:]

    # সঠিক টেলিগ্রাম API URL
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": message, 
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        print(f"📡 Telegram Response: {res_data}")
        return res_data
    except Exception as e:
        print(f"❌ Telegram Delivery Error: {e}")
        return None

@app.post("/webhook")
async def tradingview_webhook(request: Request):
    """ট্রেডিংভিউ ওয়েবহুক রিসিভার"""
    try:
        try:
            data = await request.json()
        except Exception:
            data = {}

        print(f"📥 Received Payload: {data}")
        
        ticker = data.get("ticker", "EURUSD")
        price = data.get("price", "0.0")
        rsi = data.get("rsi", "50.0")
        direction = data.get("direction", "NEW_CANDLE_OPENED")
        volume_status = data.get("volume", "CHART_ENGINE_TRIGGER")
        timeframe = data.get("timeframe", "1m")

        ai_signal = ""

        # Google Gemini দিয়ে লাইভ মার্কেট এনালাইসিস
        if client:
            try:
                prompt = (
                    "You are an elite, world-class institutional price action trader. "
                    "Analyze the raw market momentum parameters provided and make a logical trading decision. "
                    "Output your decision strictly ONLY in this exact text format:\n\n"
                    "🎯 SNIPER AI LIVE SIGNAL 🎯\n"
                    "──────────────────\n"
                    "Asset: [Insert Ticker Here]\n"
                    "Timeframe: [Insert Timeframe Here]\n"
                    "Action: [BUY / SELL / NO TRADE]\n"
                    "Entry Price: [Insert Entry Price]\n"
                    "Take Profit: [Provide Logical Target Price]\n"
                    "Stop Loss: [Provide Tight Risk Invalidated Price]\n"
                    "──────────────────\n"
                    f"Analysis: [One short sentence explaining the institutional liquidity reason]\n\n"
                    f"Market Update Data:\n"
                    f"- Asset: {ticker} ({timeframe} chart)\n"
                    f"- Price: {price}\n"
                    f"- Momentum: {direction}\n"
                    f"- Volume Status: {volume_status}\n"
                    f"- RSI: {rsi}"
                )

                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                ai_signal = response.text
            except Exception as gemini_err:
                print(f"⚠️ Gemini API Error: {gemini_err}")

        # Gemini লিমিট শেষ হয়ে গেলে বা সাড়াশব্দ না দিলে ব্যাকআপ ট্রেড বার্তা
        if not ai_signal:
            ai_signal = (
                f"🎯 *SNIPER AI ALERT* 🎯\n"
                f"──────────────────\n"
                f"*Asset:* {ticker}\n"
                f"*Timeframe:* {timeframe}\n"
                f"*Price:* {price}\n"
                f"*RSI:* {rsi}\n"
                f"──────────────────\n"
                f"⚠️ _Signal generated using Raw TradingView Engine Data._"
            )

        send_telegram_message(ai_signal)
        return {"status": "success", "info": "Signal dispatched to Telegram"}

    except Exception as e:
        print(f"❌ Core Error: {str(e)}")
        return {"status": "error", "details": str(e)}

@app.get("/")
def home():
    return {"status": "running", "engine": "Sniper AI Engine Active"}

if __name__ == "__main__": 
    uvicorn.run(app, host="0.0.0.0", port=10000)
