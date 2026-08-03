import os
import requests
import uvicorn
from fastapi import FastAPI, Request
import google.generativeai as genai

app = FastAPI()

# Environment Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Gemini SDK Configure
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def send_telegram_message(message: str):
    """টেলিগ্রাম বটে সিগন্যাল পাঠানোর ফাংশন"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram Credentials Missing!")
        return None

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": message, 
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"Telegram Delivery Error: {e}")
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
        if GEMINI_API_KEY:
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                
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

                response = model.generate_content(prompt)
                ai_signal = response.text
            except Exception as gemini_err:
                print(f"⚠️ Gemini API Error: {gemini_err}")

        # Gemini থেকে উত্তর না আসলে ব্যাকআপ বার্তা
        if not ai_signal:
            ai_signal = (
                f"🎯 *SNIPER AI ALERT* 🎯\n"
                f"──────────────────\n"
                f"*Asset:* {ticker}\n"
                f"*Timeframe:* {timeframe}\n"
                f"*Current Price:* {price}\n"
                f"*RSI:* {rsi}\n"
                f"──────────────────\n"
                f"⚠️ _Check GEMINI_API_KEY in Render Environment._"
            )

        send_telegram_message(ai_signal)
        return {"status": "success", "info": "Signal dispatched using Google Gemini"}

    except Exception as e:
        print(f"❌ Core Error: {str(e)}")
        return {"status": "error", "details": str(e)}

@app.get("/")
def home():
    return {"status": "running", "engine": "Sniper AI Powered by Google Gemini"}

if __name__ == "__main__": 
    uvicorn.run(app, host="0.0.0.0", port=10000)
