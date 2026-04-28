from fastapi import FastAPI
import requests
import os
from openai import OpenAI

app = FastAPI()

# 🔑 API KEYS
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


# 🔥 UNIVERSAL SYMBOL FORMATTER
def format_symbol(symbol: str):
    symbol = symbol.upper().strip()

    mapping = {
        # FOREX
        "XAUUSD": "XAU/USD",
        "EURUSD": "EUR/USD",
        "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY",

        # INDICES
        "US30": "DJI",
        "NAS100": "IXIC",
        "NQ": "IXIC",
        "SPX": "SPX",

        # CRYPTO
        "BTC": "BTC/USD",
        "ETH": "ETH/USD"
    }

    return mapping.get(symbol, symbol)


# 💰 GET PRICE
def get_price(symbol: str):
    try:
        url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=5).json()

        if "price" not in res:
            return None

        return float(res["price"])
    except:
        return None


# 📊 GET CANDLES (MULTI DATA)
def get_candles(symbol: str):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=30&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=5).json()

        if "values" not in res:
            return None

        return res["values"]
    except:
        return None


# 🧠 AI PRO ANALYSIS
def analyze(symbol, price, candles):

    prompt = f"""
You are an elite institutional trader.

Analyze this market using:
- Market structure (HH, HL, LH, LL)
- Liquidity zones
- Support & Resistance
- Trend direction
- Momentum
- Smart Money Concepts

Rules:
- ALWAYS provide a trade setup
- Even if weak, give best possible setup
- Risk/Reward must be >= 1.5
- Be realistic (no random numbers)

Data:
Symbol: {symbol}
Current Price: {price}
Recent Candles: {candles[:10]}

Return STRICT format:

Bias: BUY or SELL
Entry: number
Stop Loss: number
Take Profit: number
Risk/Reward: number
Confidence: %
Strength: WEAK / MEDIUM / STRONG
Reason: short explanation
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"AI error: {str(e)}"


# 🚀 MAIN ENDPOINT
@app.get("/analyze")
def analyze_market(symbol: str = "XAUUSD"):

    formatted_symbol = format_symbol(symbol)

    # 💰 price
    price = get_price(formatted_symbol)
    if not price:
        return {
            "symbol": symbol,
            "formatted_symbol": formatted_symbol,
            "error": "No price data (check API key or symbol)"
        }

    # 📊 candles
    candles = get_candles(formatted_symbol)
    if not candles:
        return {
            "symbol": symbol,
            "formatted_symbol": formatted_symbol,
            "price": price,
            "error": "No candle data"
        }

    # 🧠 AI
    analysis = analyze(formatted_symbol, price, candles)

    return {
        "symbol": symbol,
        "formatted_symbol": formatted_symbol,
        "price": price,
        "analysis": analysis
    }
