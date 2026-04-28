from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from openai import OpenAI

app = FastAPI()

# ===== CORS (frontend fix) =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== API KEYS =====
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ===== TRADING SYSTEM =====
active_trades = []
trade_history = []
user_balance = 10000
risk_per_trade = 200

# ===== SYMBOL FIX =====
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

# ===== GET CANDLES =====
def get_candles(symbol, interval):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize=20&apikey={TWELVE_API_KEY}"
    res = requests.get(url).json()

    if "values" not in res:
        return None

    closes = [float(x["close"]) for x in res["values"]]
    return closes

# ===== TREND =====
def get_trend(closes):
    if closes is None:
        return "unknown"

    if closes[0] > closes[-1]:
        return "bullish"
    else:
        return "bearish"

# ===== LEVELS =====
def get_levels(closes):
    return max(closes), min(closes)

# ===== AI =====
def ask_ai(symbol, price, t1, t5, t15, high, low):
    prompt = f"""
You are a professional scalping trader.

Symbol: {symbol}
Price: {price}

1m trend: {t1}
5m trend: {t5}
15m trend: {t15}

Recent High: {high}
Recent Low: {low}

Rules:
- Trade WITH trend (1m + 5m)
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

# ===== TRADE CHECK =====
def check_trades():
    global user_balance

    for trade in active_trades:
        if trade["status"] != "open":
            continue

        price = get_candles(trade["symbol"], "1min")[0]

        if trade["bias"] == "Buy":
            if price >= trade["tp"]:
                trade["status"] = "win"
                user_balance += risk_per_trade * 2
                trade_history.append(trade)

            elif price <= trade["sl"]:
                trade["status"] = "loss"
                user_balance -= risk_per_trade
                trade_history.append(trade)

        elif trade["bias"] == "Sell":
            if price <= trade["tp"]:
                trade["status"] = "win"
                user_balance += risk_per_trade * 2
                trade_history.append(trade)

            elif price >= trade["sl"]:
                trade["status"] = "loss"
                user_balance -= risk_per_trade
                trade_history.append(trade)

# ===== ANALYZE =====
@app.get("/analyze")
def analyze(symbol: str):

    symbol = normalize_symbol(symbol)

    c1 = get_candles(symbol, "1min")
    c5 = get_candles(symbol, "5min")
    c15 = get_candles(symbol, "15min")

    if not c1 or not c5 or not c15:
        return {"error": "No data"}

    t1 = get_trend(c1)
    t5 = get_trend(c5)
    t15 = get_trend(c15)

    high, low = get_levels(c5)

    price = c1[0]

    analysis = ask_ai(symbol, price, t1, t5, t15, high, low)

    # ===== SAVE TRADE =====
    trade = {
        "symbol": symbol,
        "entry": price,
        "tp": price + 10,
        "sl": price - 10,
        "bias": "Buy",
        "status": "open"
    }

    active_trades.append(trade)

    return {
        "symbol": symbol,
        "price": price,
        "analysis": analysis
    }

# ===== STATUS =====
@app.get("/status")
def status():
    check_trades()

    return {
        "balance": user_balance,
        "active_trades": active_trades,
        "history": trade_history
    }

# ===== ROOT =====
@app.get("/")
def home():
    return {"status": "engine running"}
