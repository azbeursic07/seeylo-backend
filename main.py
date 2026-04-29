from fastapi import FastAPI
import requests
import os
from openai import OpenAI
from datetime import datetime
import uuid

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TWELVE = os.getenv("TWELVE_API_KEY")

# =====================
# STATE
# =====================
trades = []
balance = 10000


# =====================
# SYMBOL MAP
# =====================
def normalize(symbol):
    s = symbol.upper()

    mapping = {
        "XAUUSD": "XAU/USD",
        "EURUSD": "EUR/USD",
        "BTC": "BTC/USD",
        "ETH": "ETH/USD",
        "NQ": "QQQ",  # proxy
    }

    return mapping.get(s, s)


# =====================
# PRICE
# =====================
def get_price(symbol):
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE}"
    r = requests.get(url).json()

    if "price" in r:
        return float(r["price"])

    return None


# =====================
# CANDLES
# =====================
def get_candles(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=30&apikey={TWELVE}"
    r = requests.get(url).json()

    if "values" not in r:
        return None

    txt = ""
    for c in r["values"][:20]:
        txt += f"{c['close']},"

    return txt


# =====================
# AI ENGINE
# =====================
def ai(symbol, price, candles):

    prompt = f"""
You are a professional scalping trader.

Give BEST trade setup.

Symbol: {symbol}
Price: {price}

Candles:
{candles}

Rules:
- Always give trade
- RR >= 1.5
- realistic tight levels
- follow trend + liquidity

FORMAT EXACTLY:

Bias:
Entry:
Stop Loss:
Take Profit:
Confidence:
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message.content


# =====================
# PARSE
# =====================
def parse(text):
    d = {}

    for l in text.split("\n"):
        if "Bias" in l:
            d["bias"] = l.split(":")[1].strip()
        if "Entry" in l:
            d["entry"] = float(l.split(":")[1])
        if "Stop" in l:
            d["sl"] = float(l.split(":")[1])
        if "Take" in l:
            d["tp"] = float(l.split(":")[1])

    return d


# =====================
# ANALYZE
# =====================
@app.get("/analyze")
def analyze(symbol: str):

    original = symbol.upper()
    norm = normalize(original)

    price = get_price(norm)
    if not price:
        return {"error": "no price"}

    candles = get_candles(norm)
    if not candles:
        return {"error": "no candles"}

    raw = ai(norm, price, candles)
    t = parse(raw)

    # =====================
    # 🔥 DYNAMIC SCALING (NQ)
    # =====================
    if original == "NQ":
        try:
            nq_est = 27000  # approx anchor
            scale = nq_est / price

            t["entry"] *= scale
            t["sl"] *= scale
            t["tp"] *= scale

            price = price * scale

        except:
            pass

    trade = {
        "id": str(uuid.uuid4()),
        "symbol": original,
        "entry": round(t["entry"], 2),
        "sl": round(t["sl"], 2),
        "tp": round(t["tp"], 2),
        "bias": t["bias"],
        "status": "ACTIVE",
        "created": str(datetime.now())
    }

    trades.append(trade)

    return {
        "price": round(price, 2),
        "trade": trade,
        "analysis": raw
    }


# =====================
# TRACK
# =====================
@app.get("/trades")
def track():

    global balance

    results = []

    for t in trades:

        if t["status"] != "ACTIVE":
            results.append(t)
            continue

        norm = normalize(t["symbol"])
        price = get_price(norm)

        if not price:
            continue

        # scaling back if NQ
        if t["symbol"] == "NQ":
            price *= (t["entry"] / (t["entry"] / 42))

        profit = 0

        if t["bias"] == "BUY":
            profit = price - t["entry"]

            if price >= t["tp"]:
                t["status"] = "TP HIT"
                balance += profit

            elif price <= t["sl"]:
                t["status"] = "SL HIT"
                balance += profit

        else:
            profit = t["entry"] - price

            if price <= t["tp"]:
                t["status"] = "TP HIT"
                balance += profit

            elif price >= t["sl"]:
                t["status"] = "SL HIT"
                balance += profit

        t["profit"] = round(profit, 2)
        results.append(t)

    return {
        "balance": round(balance, 2),
        "trades": results
    }


# =====================
# RESET
# =====================
@app.get("/reset")
def reset():
    global trades, balance
    trades = []
    balance = 10000
    return {"status": "reset"}
