import os
import requests
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from openai import OpenAI

app = FastAPI()

# পরিবেশ ভেরিয়েবল (Environment Variables)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# OpenAI ক্লায়েন্ট ইনিশিয়ালাইজেশন
client = OpenAI(api_key=OPENAI_API_KEY)

def send_telegram_message(message: str):
    """টেলিগ্রাম বটে এআই এর ফাইনাল সিগন্যাল পুশ করার প্রাতিষ্ঠানিক ফাংশন"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": message, 
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"Telegram Delivery Error: {e}")
        return None

@app.post("/webhook")
async def tradingview_webhook(request: Request):
    """ট্রেডিংভিউ থেকে লাইভ চার্ট ডেটা রিসিভ করার মূল এন্ডপয়েন্ট"""
    try:
        data = await request.json()
        
        ticker = data.get("ticker", "UNKNOWN_ASSET")
        price = data.get("price", "0.0")
        rsi = data.get("rsi", "50.0")
        direction = data.get("direction", "NEUTRAL_SCAN")
        volume_status = data.get("volume", "NORMAL_VOLUME")
        timeframe = data.get("timeframe", "5m")
        
        system_prompt = (
            "You are an elite, world-class institutional price action trader. You absolute hate retail indicator traps. "
            "Analyze the raw market momentum parameters provided and make a logical trading decision. "
            "Do not give fake signals. If the market is choppy or risky, set Action to 'NO TRADE'. "
            "You must strictly output your decision ONLY in this exact text format:\n\n"
            "🎯 SNIPER AI LIVE SIGNAL 🎯\n"
            "──────────────────\n"
            "Asset: [Insert Ticker Here]\n"
            "Timeframe: [Insert Timeframe Here]\n"
            "Action: [BUY / SELL / NO TRADE] \n"
            "Entry Price: [Insert Entry Price]\n"
            "Take Profit: [Provide Logical Target Price]\n"
            "Stop Loss: [Provide Tight Risk Invalidated Price]\n"
            "──────────────────\n"
            "Analysis: [One short sentence explaining the institutional liquidity reason]"
        )
        
        user_prompt = (
            f"Market Update for {ticker} ({timeframe} chart):\n"
            f"- Current Market Price: {price}\n"
            f"- Momentum Indicator Setup: {direction}\n"
            f"- Institutional Volume Status: {volume_status}\n"
            f"- Relative Strength Index (RSI): {rsi}\n\n"
            f"Provide immediate structural execution plan based on pure price action rules."
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
        
        send_telegram_message(ai_signal)
        return {"status": "success", "info": "Signal successfully dispatched to Telegram"}
        
    except Exception as e:
        print(f"Server Internal Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/")
def home():
    return {"status": "running", "engine": "Sniper AI Premium v7 Active"}

if __name__ == "__main__": 
    uvicorn.run(app, host="0.0.0.0", port=10000)
