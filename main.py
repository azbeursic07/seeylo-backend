from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from openai import OpenAI

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# 🔥 SYMBOL MAP
def normalize_symbol(symbol):
    symbol = symbol.upper()
    mapping = {
        "NQ": "NAS100",
        "XAU": "XAUUSD",
        "GOLD": "XAUUSD",
        "BTC": "BTC/USD",
        "ES": "SPX500"
    }
    return mapping.get(symbol, symbol)

# 🔥 FETCH CANDLES
def get_candles(symbol, interval):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize=20&apikey={TWELVE_API_KEY}"
    res = requests.get(url).json()

    if "values" not in res:
        return None

    closes = [float(x["close"]) for x in res["values"]]
    return closes

# 🔥 TREND DETECTION
def get_trend(closes):
    if closes is None:
        return "unknown"

    if closes[0] > closes[-1]:
        return "bullish"
    else:
        return "bearish"

# 🔥 HIGH / LOW
def get_levels(closes):
    return max(closes), min(closes)

# 🤖 AI DECISION
def ask_ai(symbol, price, trend1, trend5, trend15, high, low):
    prompt = f"""
You are an elite scalping trader.

Symbol: {symbol}
Price: {price}

1m trend: {trend1}
5m trend: {trend5}
15m trend: {trend15}

Recent High: {high}
Recent Low: {low}

Rules:
- Trade WITH trend (1m + 5m)
- If mixed → lower confidence
- Entry must be near high/low or pullback
- RR >= 1.5

Return:

Type: HIGH or LOW
Bias: Buy or Sell
Entry:
Stop Loss:
Take Profit:
Risk/Reward:
Confidence:
Reason:
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content

# 🚀 MAIN
@app.get("/analyze")
def analyze(symbol: str):

    symbol = normalize_symbol(symbol)

    # candles
    c1 = get_candles(symbol, "1min")
    c5 = get_candles(symbol, "5min")
    c15 = get_candles(symbol, "15min")

    if not c1 or not c5 or not c15:
        return {"error": "No candle data"}

    # trend
    t1 = get_trend(c1)
    t5 = get_trend(c5)
    t15 = get_trend(c15)

    # levels
    high, low = get_levels(c5)

    # price
    price = c1[0]

    # AI
    analysis = ask_ai(symbol, price, t1, t5, t15, high, low)

    return {
        "symbol": symbol,
        "price": price,
        "trend_1m": t1,
        "trend_5m": t5,
        "trend_15m": t15,
        "high": high,
        "low": low,
        "analysis": analysis
    }

@app.get("/")
def home():
    return {"status": "engine running"}
