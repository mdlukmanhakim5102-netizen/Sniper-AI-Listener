import os
import requests
import uvicorn
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()

# পরিবেশ ভেরিয়েবল (Environment Variables)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# OpenAI ইনিশিয়ালাইজেশন
client = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print(f"OpenAI Client Init Failed: {e}")

def send_telegram_message(message: str):
    """টেলিগ্রাম বটে এআই এর ফাইনাল সিগন্যাল পুশ করার প্রাতিষ্ঠানিক ফাংশন"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram Credentials Missing in Render Environment!")
        return None

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": message, 
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"Telegram Delivery Status: {response.status_code}")
        return response.json()
    except Exception as e:
        print(f"Telegram Delivery Error: {e}")
        return None

@app.post("/webhook")
async def tradingview_webhook(request: Request):
    """ট্রেডিংভিউ থেকে লাইভ চার্ট ডেটা রিসিভ করার মূল এন্ডপয়েন্ট"""
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

        # ১. OpenAI দিয়ে সিগন্যাল জেনারেট করার চেষ্টা
        if client:
            try:
                system_prompt = (
                    "You are an elite institutional price action trader. "
                    "Analyze the market parameters and make a logical trading decision. "
                    "Output your decision strictly in this exact format:\n\n"
                    "🎯 SNIPER AI LIVE SIGNAL 🎯\n"
                    "──────────────────\n"
                    "Asset: [Insert Ticker Here]\n"
                    "Timeframe: [Insert Timeframe Here]\n"
                    "Action: [BUY / SELL / NO TRADE] \n"
                    "Entry Price: [Insert Entry Price]\n"
                    "Take Profit: [Provide Logical Target Price]\n"
                    "Stop Loss: [Provide Tight Risk Invalidated Price]\n"
                    "──────────────────\n"
                    "Analysis: [One short sentence explaining the reason]"
                )
                
                user_prompt = (
                    f"Market Update for {ticker} ({timeframe} chart):\n"
                    f"- Current Market Price: {price}\n"
                    f"- Momentum Setup: {direction}\n"
                    f"- Volume Status: {volume_status}\n"
                    f"- RSI: {rsi}\n\n"
                    f"Provide immediate structural execution plan based on price action."
                )

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=250,
                    temperature=0.3
                )
                ai_signal = response.choices[0].message.content
            except Exception as openai_err:
                print(f"⚠️ OpenAI Error: {openai_err}")

        # ২. যদি OpenAI ফেইল করে তবে ডিফল্ট ফরমেটে টেলিগ্রামে ডাটা যাবে (যাতে ৫০২ এরর না আসে)
        if not ai_signal:
            ai_signal = (
                f"🎯 *SNIPER AI ALERT* 🎯\n"
                f"──────────────────\n"
                f"*Asset:* {ticker}\n"
                f"*Timeframe:* {timeframe}\n"
                f"*Current Price:* {price}\n"
                f"*RSI:* {rsi}\n"
                f"──────────────────\n"
                f"⚠️ _OpenAI Key Check Needed! Raw Data Dispatched._"
            )

        # টেলিগ্রামে সিগন্যাল পুশ
        send_telegram_message(ai_signal)
        return {"status": "success", "info": "Signal dispatched successfully"}

    except Exception as e:
        print(f"❌ Core Error: {str(e)}")
        return {"status": "handled_error", "details": str(e)}

@app.get("/")
def home():
    return {"status": "running", "engine": "Sniper AI Premium Active"}

if __name__ == "__main__": 
    uvicorn.run(app, host="0.0.0.0", port=10000)
