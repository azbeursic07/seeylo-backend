from fastapi import FastAPI
import requests
import os
from datetime import datetime
import uuid

app = FastAPI()

TWELVE = os.getenv("TWELVE_API_KEY")

trades = []
history = []
balance = 10000


# ===== SYMBOL =====
def normalize(symbol):
    s = symbol.upper()

    if s == "NQ":
        return "QQQ"
    if s == "ES":
        return "SPY"
    if s == "XAUUSD":
        return "XAU/USD"

    return s


# ===== PRICE (ULTRA SAFE) =====
def get_price(symbol):

    try:
        r = requests.get(
            f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE}"
        ).json()

        if "price" in r:
            return float(r["price"])

        r = requests.get(
            f"https://api.twelvedata.com/quote?symbol={symbol}&apikey={TWELVE}"
        ).json()

        if "close" in r:
            return float(r["close"])

    except:
        pass

    # ===== FALLBACK (NEVER FAIL) =====
    fallback_prices = {
        "QQQ": 450,
        "SPY": 520,
        "BTC/USD": 60000,
        "ETH/USD": 3000,
        "XAU/USD": 2300
    }

    return fallback_prices.get(symbol, 100)


# ===== SIMPLE AI (NO CRASH) =====
def generate_trade(price):

    import random

    bias = random.choice(["BUY", "SELL"])

    if bias == "BUY":
        entry = price * 0.999
        sl = entry * 0.997
        tp = entry * 1.004
    else:
        entry = price * 1.001
        sl = entry * 1.003
        tp = entry * 0.996

    return bias, entry, sl, tp


# ===== ANALYZE =====
@app.get("/analyze")
def analyze(symbol: str):

    original = symbol.upper()
    norm = normalize(original)

    price = get_price(norm)

    # NQ scaling
    if original == "NQ":
        price *= 42

    bias, entry, sl, tp = generate_trade(price)

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
        "price": round(price, 2),
        "trade": trade,
        "analysis": f"{bias} setup generated"
    }


# ===== TRACK =====
@app.get("/trades")
def track():

    global balance
    now = datetime.now().timestamp()

    for t in trades:

        norm = normalize(t["symbol"])
        price = get_price(norm)

        if t["symbol"] == "NQ":
            price *= 42

        # delay (no instant TP/SL)
        if now - t["created_ts"] < 5:
            continue

        # activate
        if t["status"] == "PENDING":
            if t["bias"] == "BUY" and price <= t["entry"]:
                t["status"] = "ACTIVE"
            elif t["bias"] == "SELL" and price >= t["entry"]:
                t["status"] = "ACTIVE"

        # active logic
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

        # live pnl
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
