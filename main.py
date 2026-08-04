import os
import requests
import uvicorn
from fastapi import FastAPI, Request
import google.generativeai as genai

app = FastAPI()

# Render Environment Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Gemini Config
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY.strip())
    except Exception as e:
        print(f"Gemini Init Error: {e}")

def send_telegram_message(message: str):
    """টেলিগ্রাম বটে মেসেজ পাঠানোর নিখুঁত প্রোডাকশন ফাংশন"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram Credentials Missing!")
        return None
    
    token = TELEGRAM_BOT_TOKEN.strip()
    # চূড়ান্ত ডোমেন সংশোধন: অবশই api.telegram.org হতে হবে
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID.strip(),
        "text": message,
        "parse_mode": "Markdown"
    }
    
    # জেমিনির স্পেশাল ক্যারেক্টার জনিত মার্কডাউন পার্স এরর হ্যান্ডলিং ফলব্যাক
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        
        if not response.ok:
            print("⚠️ Markdown parse failed, retrying with raw text...")
            payload.pop("parse_mode", None)
            response = requests.post(url, json=payload, timeout=10)
            res_data = response.json()
            
        print(f"📡 Telegram Response: {res_data}")
        return res_data
        
    except Exception as e:
        print("⚠️ Direct request failed, trying fallback without parse_mode...")
        try:
            payload.pop("parse_mode", None)
            response = requests.post(url, json=payload, timeout=10)
            return response.json()
        except Exception as fallback_err:
            print(f"❌ Telegram Delivery Error: {fallback_err}")
            return None

@app.post("/webhook")
async def tradingview_webhook(request: Request):
    """ট্রেডিংভিউ ওয়েবহুক রিসিভার (Gemini 1.5 Flash ভার্সন)"""
    try:
        try:
            data = await request.json()
        except Exception:
            data = {}
            
        print(f"📥 Received Payload: {data}")
        
        # এম্পটি পে-লোড বা ফাঁকা ডাটা আসলে প্রসেসিং ইগনোর করা
        if not data:
            return {
                "status": "ignored",
                "reason": "Empty payload"
            }
        
        # ডাবল কি হ্যান্ডলিং (ticker বা asset দুই ধরনের payload-ই কাজ করবে)
        ticker = data.get("ticker") or data.get("asset", "EURUSD")
        price = data.get("price", "0.0")
        rsi = data.get("rsi", "50.0")
        direction = data.get("direction", "NEW_CANDLE_OPENED")
        volume_status = data.get("volume", "CHART_ENGINE_TRIGGER")
        timeframe = data.get("timeframe", "1m")
        
        ai_signal = ""

        # Google Gemini লাইভ মার্কেট এনালাইসিস
        if GEMINI_API_KEY:
            try:
                # v1beta 404 ক্লাউড এরর এড়াতে সুনির্দিষ্ট মডেল পাথ কনফিগারেশন
                model = genai.GenerativeModel('models/gemini-1.5-flash')
                
                prompt = (
                    "You are an elite, world-class institutional price action trader. "
                    "Analyze the raw market momentum parameters provided and make a logical trading decision. "
                    "Output your decision strictly ONLY in this exact text format:\n\n"
                    "🎯 SNIPER AI LIVE SIGNAL 🎯\n"
                    "──────────────────\n"
                    f"Ticker: {ticker}\n"
                    f"Timeframe: {timeframe}\n"
                    "Action: [BUY / SELL / NO TRADE]\n"
                    f"Entry Price: {price}\n"
                    "Take Profit: [Provide Logical Target Price]\n"
                    "Stop Loss: [Provide Tight Risk Invalidated Price]\n"
                    "──────────────────\n"
                    f"Analysis: [One short sentence explaining the institutional liquidity reason]\n\n"
                    f"Market Update Data:\n"
                    f"- Ticker: {ticker} ({timeframe} chart)\n"
                    f"- Price: {price}\n"
                    f"- Momentum: {direction}\n"
                    f"- Volume Status: {volume_status}\n"
                    f"- RSI: {rsi}"
                )
                response = model.generate_content(prompt)
                
                # ক্র্যাশ প্রোটেকশন সেফটি লজিক
                if hasattr(response, "text") and response.text:
                    ai_signal = response.text
                else:
                    ai_signal = ""
                    print("⚠️ Gemini response did not contain text.")
                    
            except Exception as gemini_err:
                print(f"⚠️ Gemini API Error: {gemini_err}")

        # ব্যাকআপ অ্যালার্ট (যদি জেমিনি রেসপন্স খালি থাকে)
        if not ai_signal:
            ai_signal = (
                f"🎯 *SNIPER AI ALERT* 🎯\n"
                f"──────────────────\n"
                f"*Ticker:* {ticker}\n"
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
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
