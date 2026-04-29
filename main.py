from fastapi import FastAPI
import requests
import os
from openai import OpenAI
from datetime import datetime
import uuid

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
TWELVE = os.getenv("TWELVE_API_KEY")

# ===== STATE =====
trades = []
balance = 10000
history = []

# ===== SYMBOL NORMALIZATION =====
def normalize(symbol):
    s = symbol.upper()
    mapping = {
        "XAUUSD": "XAU/USD",
        "EURUSD": "EUR/USD",
        "BTC": "BTC/USD",
        "ETH": "ETH/USD",
        "NQ": "QQQ"
    }
    return mapping.get(s, s)

# ===== PRICE =====
def get_price(symbol):
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE}"
    r = requests.get(url).json()
    if "price" in r:
        return float(r["price"])
    return None

# ===== CANDLES =====
def get_candles(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=30&apikey={TWELVE}"
    r = requests.get(url).json()

    if "values" not in r:
        return None

    candles = ""
    for c in r["values"][:20]:
        candles += f"{c['close']},"

    return candles

# ===== AI ENGINE =====
def ai(symbol, price, candles):

    prompt = f"""
You are a professional scalper.

Give ONE best trade setup.

Symbol: {symbol}
Price: {price}

Candles:
{candles}

Rules:
- High probability setup
- RR >= 1.5
- Tight but realistic SL
- Follow trend

FORMAT:

Bias:
Confidence:
Reason:
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message.content


# ===== ANALYZE =====
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

    analysis = ai(norm, price, candles)

    # ===== CREATE REALISTIC TRADE =====
    current = price

    # scaling for NQ
    if original == "NQ":
        current = current * 42  # approx

    # direction
    bias = "BUY" if "BUY" in analysis.upper() else "SELL"

    if bias == "BUY":
        entry = current * 0.999
        sl = entry * 0.997
        tp = entry * 1.004
    else:
        entry = current * 1.001
        sl = entry * 1.003
        tp = entry * 0.996

    trade = {
        "id": str(uuid.uuid4()),
        "symbol": original,
        "entry": round(entry, 2),
        "sl": round(sl, 2),
        "tp": round(tp, 2),
        "bias": bias,
        "status": "PENDING",
        "created": str(datetime.now()),
        "profit": 0
    }

    trades.append(trade)

    return {
        "price": round(current, 2),
        "trade": trade,
        "analysis": analysis
    }


# ===== TRACK =====
@app.get("/trades")
def track():

    global balance

    for t in trades:

        norm = normalize(t["symbol"])
        price = get_price(norm)

        if not price:
            continue

        if t["symbol"] == "NQ":
            price = price * 42

        # ===== STATE MACHINE =====

        # activate trade
        if t["status"] == "PENDING":
            if t["bias"] == "BUY" and price <= t["entry"]:
                t["status"] = "ACTIVE"
            elif t["bias"] == "SELL" and price >= t["entry"]:
                t["status"] = "ACTIVE"

        # active trade logic
        elif t["status"] == "ACTIVE":

            if t["bias"] == "BUY":

                if price >= t["tp"]:
                    profit = t["tp"] - t["entry"]
                    t["status"] = "TP HIT"
                    balance += profit

                    history.append({
                        "date": str(datetime.now().date()),
                        "profit": round(profit, 2)
                    })

                elif price <= t["sl"]:
                    profit = t["entry"] - t["sl"]
                    t["status"] = "SL HIT"
                    balance -= profit

                    history.append({
                        "date": str(datetime.now().date()),
                        "profit": -round(profit, 2)
                    })

            else:

                if price <= t["tp"]:
                    profit = t["entry"] - t["tp"]
                    t["status"] = "TP HIT"
                    balance += profit

                    history.append({
                        "date": str(datetime.now().date()),
                        "profit": round(profit, 2)
                    })

                elif price >= t["sl"]:
                    profit = t["sl"] - t["entry"]
                    t["status"] = "SL HIT"
                    balance -= profit

                    history.append({
                        "date": str(datetime.now().date()),
                        "profit": -round(profit, 2)
                    })

        # live profit
        if t["status"] == "ACTIVE":
            if t["bias"] == "BUY":
                t["profit"] = round(price - t["entry"], 2)
            else:
                t["profit"] = round(t["entry"] - price, 2)

    return {
        "balance": round(balance, 2),
        "trades": trades
    }


# ===== HISTORY =====
@app.get("/history")
def get_history():
    return history


# ===== RESET =====
@app.get("/reset")
def reset():
    global trades, balance, history
    trades = []
    history = []
    balance = 10000
    return {"status": "reset"}
