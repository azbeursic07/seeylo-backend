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
history = []
balance = 10000

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

# ===== PRICE (robust) =====
def get_price(symbol):
    try:
        r = requests.get(f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE}").json()
        if "price" in r:
            return float(r["price"])

        r = requests.get(f"https://api.twelvedata.com/quote?symbol={symbol}&apikey={TWELVE}").json()
        if "close" in r:
            return float(r["close"])

    except:
        return None

    return None

# ===== CANDLES =====
def get_candles(symbol):
    r = requests.get(
        f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=30&apikey={TWELVE}"
    ).json()

    if "values" not in r:
        return None

    return ",".join([c["close"] for c in r["values"][:20]])

# ===== AI =====
def ai(symbol, price, candles):
    prompt = f"""
You are a pro scalper.

Give ONE best trade setup.

Symbol: {symbol}
Price: {price}
Candles: {candles}

Rules:
- High probability
- RR >= 1.5

FORMAT:
Bias:
Confidence:
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

    current = price

    # ===== NQ scaling =====
    if original == "NQ":
        current = current * 42

    bias = "BUY" if "BUY" in analysis.upper() else "SELL"

    # ===== REALISTIC ENTRY =====
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
        "created_ts": datetime.now().timestamp(),
        "profit": 0
    }

    trades.insert(0, trade)

    return {
        "price": round(current, 2),
        "trade": trade,
        "analysis": analysis
    }

# ===== TRACK =====
@app.get("/trades")
def track():
    global balance

    now = datetime.now().timestamp()

    for t in trades:

        norm = normalize(t["symbol"])
        price = get_price(norm)

        if not price:
            continue

        if t["symbol"] == "NQ":
            price *= 42

        # ===== delay (fix instant TP/SL) =====
        if now - t["created_ts"] < 5:
            continue

        # ===== activate =====
        if t["status"] == "PENDING":
            if t["bias"] == "BUY" and price <= t["entry"]:
                t["status"] = "ACTIVE"
            elif t["bias"] == "SELL" and price >= t["entry"]:
                t["status"] = "ACTIVE"

        # ===== active =====
        elif t["status"] == "ACTIVE":

            if t["bias"] == "BUY":

                if price >= t["tp"]:
                    profit = t["tp"] - t["entry"]
                    t["status"] = "TP HIT"
                    balance += profit
                    history.append({"date": str(datetime.now().date()), "profit": round(profit, 2)})

                elif price <= t["sl"]:
                    loss = t["entry"] - t["sl"]
                    t["status"] = "SL HIT"
                    balance -= loss
                    history.append({"date": str(datetime.now().date()), "profit": -round(loss, 2)})

            else:

                if price <= t["tp"]:
                    profit = t["entry"] - t["tp"]
                    t["status"] = "TP HIT"
                    balance += profit
                    history.append({"date": str(datetime.now().date()), "profit": round(profit, 2)})

                elif price >= t["sl"]:
                    loss = t["sl"] - t["entry"]
                    t["status"] = "SL HIT"
                    balance -= loss
                    history.append({"date": str(datetime.now().date()), "profit": -round(loss, 2)})

        # ===== live pnl =====
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
    global trades, history, balance
    trades = []
    history = []
    balance = 10000
    return {"status": "reset"}
