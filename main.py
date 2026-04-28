from fastapi import FastAPI
import requests
import os
from openai import OpenAI

app = FastAPI()

# API KEYS
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


# 🔥 SYMBOL FIX (NAJBOLJ POMEMBNO)
def format_symbol(symbol: str):
    symbol = symbol.upper().strip()

    mapping = {
        "XAUUSD": "XAU/USD",
        "EURUSD": "EUR/USD",
        "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY",
        "US30": "DJI",
        "NAS100": "IXIC",
        "NQ": "IXIC",
        "SPX": "SPX",
        "BTC": "BTC/USD",
        "ETH": "ETH/USD"
    }

    return mapping.get(symbol, symbol)


# 📈 GET PRICE
def get_price(symbol: str):
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_API_KEY}"
    res = requests.get(url).json()

    if "price" not in res:
        return None

    return float(res["price"])


# 📊 GET CANDLES
def get_candles(symbol: str):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=30&apikey={TWELVE_API_KEY}"
    res = requests.get(url).json()

    if "values" not in res:
        return None

    return res["values"]


# 🧠 AI ANALYSIS
def analyze(symbol, price, candles):

    prompt = f"""
You are a professional trading AI.

Analyze this market:

Symbol: {symbol}
Current Price: {price}
Recent Candles: {candles[:5]}

Return STRICT format:

Bias: BUY or SELL
Entry: number
Stop Loss: number
Take Profit: number
Risk/Reward: number
Confidence: %
Reason: short explanation
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


# 🚀 MAIN ENDPOINT
@app.get("/analyze")
def analyze_market(symbol: str = "XAUUSD"):

    formatted_symbol = format_symbol(symbol)

    price = get_price(formatted_symbol)

    if not price:
        return {
            "symbol": symbol,
            "error": "No price data (check API key or symbol)"
        }

    candles = get_candles(formatted_symbol)

    if not candles:
        return {
            "symbol": symbol,
            "price": price,
            "error": "No candle data"
        }

    analysis = analyze(formatted_symbol, price, candles)

    return {
        "symbol": symbol,
        "formatted_symbol": formatted_symbol,
        "price": price,
        "analysis": analysis
    }
