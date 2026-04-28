from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from openai import OpenAI

app = FastAPI()

# 🔓 allow frontend (Lovable)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔑 API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# 🧠 SYMBOL FIX (VERY IMPORTANT)
def normalize_symbol(symbol):
    symbol = symbol.upper()

    mapping = {
        "NQ": "NAS100",
        "NAS": "NAS100",
        "US100": "NAS100",
        "ES": "SPX500",
        "SPX": "SPX500",
        "XAU": "XAUUSD",
        "GOLD": "XAUUSD",
        "BTC": "BTC/USD"
    }

    return mapping.get(symbol, symbol)

# 📊 GET REAL PRICE
def get_price(symbol):
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVEDATA_API_KEY}"
    res = requests.get(url).json()

    if "price" not in res:
        return None

    return float(res["price"])

# 🤖 AI ANALYSIS
def ask_ai(symbol, price):
    prompt = f"""
You are a professional scalping trader.

Symbol: {symbol}
Current Price: {price}

You MUST always return a trade setup.

Classify setup quality:

- HIGH QUALITY → strong setup
- LOW QUALITY → weak/risky

Rules:
- Prefer RR >= 2
- If no strong setup → still return LOW QUALITY trade
- Be realistic with prices (close to current price)

Return EXACT format:

Type: HIGH or LOW
Bias: Buy or Sell
Entry: number
Stop Loss: number
Take Profit: number
Risk/Reward: number
Confidence: %
Reason: short explanation
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content

# 🚀 MAIN ENDPOINT
@app.get("/analyze")
def analyze(symbol: str):

    symbol = normalize_symbol(symbol)

    price = get_price(symbol)

    if price is None:
        return {"error": "Could not fetch price"}

    analysis = ask_ai(symbol, price)

    return {
        "symbol": symbol,
        "price": price,
        "analysis": analysis
    }

# 🧪 HEALTH CHECK
@app.get("/")
def home():
    return {"status": "running"}
