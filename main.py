from fastapi import FastAPI
import requests
import os

app = FastAPI()

OPENAI_KEY = os.getenv("OPENAI_KEY")
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")


def get_price(symbol):
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_API_KEY}"
        res = requests.get(url).json()

        if "price" in res:
            return float(res["price"])
        else:
            return None
    except:
        return None


def ask_ai(symbol, price):
    prompt = f"""
You are a professional scalping trader.

Symbol: {symbol}
Current Price: {price}

Analyze for short-term trade (1m–15m).

Rules:
- Use REAL current price
- Entry must be close to current price
- Minimum RR = 1.5

Return EXACT format:

Bias: (Buy or Sell)
Entry: ...
Stop Loss: ...
Take Profit: ...
Risk/Reward: ...
Confidence: (1-100%)
Reason: (short explanation)
"""

    headers = {
        "Authorization": f"Bearer {OPENAI_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }

    res = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data
    )

    response = res.json()

    if "choices" not in response:
        return {"error": response}

    return response["choices"][0]["message"]["content"]


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/analyze")
def analyze(symbol: str):
    price = get_price(symbol)

    if price is None:
        return {"error": "Could not fetch price"}

    ai = ask_ai(symbol, price)

    return {
        "symbol": symbol,
        "price": price,
        "analysis": ai
    }
