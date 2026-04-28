from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from openai import OpenAI

app = FastAPI()

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== KEYS =====
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ===== SYMBOL MAP =====
def map_symbol(symbol):
    symbol = symbol.upper()
    mapping = {
        "NQ": "NQ=F",
        "ES": "ES=F",
        "SPX": "SPY",
        "XAUUSD": "XAU/USD",
        "GOLD": "XAU/USD",
        "BTC": "BTC/USD",
        "ETH": "ETH/USD"
    }
    return mapping.get(symbol, symbol)

# ===== GET PRICE =====
def get_price(symbol):
    mapped = map_symbol(symbol)

    try:
        url = f"https://api.twelvedata.com/price?symbol={mapped}&apikey={TWELVE_API_KEY}"
        res = requests.get(url, timeout=5)
        data = res.json()

        if "price" not in data:
            return None

        return float(data["price"])

    except:
        return None

# ===== GET CANDLES =====
def get_candles(symbol, interval="5min"):
    mapped = map_symbol(symbol)

    url = f"https://api.twelvedata.com/time_series?symbol={mapped}&interval={interval}&outputsize=50&apikey={TWELVE_API_KEY}"

    res = requests.get(url, timeout=5)
    data = res.json()

    if "values" not in data:
        return None

    return data["values"]

# ===== TREND =====
def detect_trend(candles):
    closes = [float(c["close"]) for c in candles]

    if closes[-1] > closes[0]:
        return "UP"
    else:
        return "DOWN"

# ===== LEVELS =====
def get_levels(candles):
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]

    return max(highs), min(lows)

# ===== AI ENGINE =====
def get_ai_analysis(symbol, price, trend, high, low):

    prompt = f"""
You are an elite scalping trader.

Symbol: {symbol}
Current price: {price}
Trend: {trend}
Resistance: {high}
Support: {low}

Rules:
- Trade ONLY with trend
- Entry near support/resistance or pullback
- RR >= 1.5
- High probability setup only

Return ONLY JSON:

{{
  "bias": "",
  "entry": 0,
  "sl": 0,
  "tp": 0,
  "rr": 0,
  "confidence": 0,
  "reason": ""
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content

# ===== ANALYZE =====
@app.get("/analyze")
def analyze(symbol: str):

    price = get_price(symbol)

    if not price:
        return {"error": "No price data"}

    candles = get_candles(symbol)

    if not candles:
        return {"error": "No candle data"}

    trend = detect_trend(candles)
    high, low = get_levels(candles)

    try:
        analysis = get_ai_analysis(symbol, price, trend, high, low)
    except Exception as e:
        return {"error": str(e)}

    return {
        "symbol": symbol.upper(),
        "price": price,
        "trend": trend,
        "resistance": high,
        "support": low,
        "analysis": analysis
    }

# ===== HEALTH =====
@app.get("/")
def root():
    return {"status": "engine running"}
