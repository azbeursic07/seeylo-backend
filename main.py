from fastapi import FastAPI
import requests
import os
from openai import OpenAI

app = FastAPI()

# 🔑 KEYS
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


# 🔥 SYMBOL FORMAT
def format_symbol(symbol: str):
    symbol = symbol.upper().strip()

    mapping = {
        # FOREX
        "XAUUSD": "XAU/USD",
        "EURUSD": "EUR/USD",
        "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY",

        # INDICES (proxy)
        "NQ": "QQQ",
        "NAS100": "QQQ",
        "US30": "DIA",
        "SPX": "SPY",

        # CRYPTO
        "BTC": "BTC/USD",
        "ETH": "ETH/USD"
    }

    return mapping.get(symbol, symbol)


# 🔁 QQQ → NQ scaling
def convert_to_nq(price):
    return price * 27


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


# 📊 GET CANDLES
def get_candles(symbol: str):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=30&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=5).json()

        if "values" not in res:
            return None

        return res["values"]
    except:
        return None


# 🧠 AI ANALYSIS (PRO)
def analyze(symbol, price, candles):

    prompt = f"""
You are an elite institutional trader.

Analyze using:
- Market structure
- Liquidity
- Support & Resistance
- Trend & momentum

Rules:
- ALWAYS give best possible trade
- Risk/Reward >= 1.5

Data:
Symbol: {symbol}
Price: {price}
Candles: {candles[:10]}

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

    price = get_price(formatted_symbol)

    if not price:
        return {
            "symbol": symbol,
            "formatted_symbol": formatted_symbol,
            "error": "No price data (check API key or symbol)"
        }

    candles = get_candles(formatted_symbol)

    if not candles:
        return {
            "symbol": symbol,
            "formatted_symbol": formatted_symbol,
            "price": price,
            "error": "No candle data"
        }

    analysis = analyze(formatted_symbol, price, candles)

    # 🔥 NQ conversion
    price_nq = None
    if symbol.upper() in ["NQ", "NAS100"]:
        price_nq = convert_to_nq(price)

    return {
        "symbol": symbol,
        "formatted_symbol": formatted_symbol,
        "price": price,
        "price_nq": price_nq,
        "analysis": analysis
    }
