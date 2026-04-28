from fastapi import FastAPI
import requests
import os
import numpy as np

app = FastAPI()

API_KEY = os.getenv("TWELVEDATA_API_KEY")

# ======================
# HEALTH CHECK
# ======================
@app.get("/")
def root():
    return {"status": "running"}

# ======================
# FETCH DATA (FIXED)
# ======================
def get_data(symbol):
    # FIX SYMBOLS
    if symbol.upper() == "XAUUSD":
        symbol = "XAU/USD"
    if symbol.upper() == "BTC":
        symbol = "BTC/USD"

    try:
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=100&apikey={API_KEY}"
        r = requests.get(url, timeout=10).json()

        if r.get("status") != "ok":
            return None

        values = r.get("values")
        if not values:
            return None

        closes = [float(c["close"]) for c in values][::-1]
        highs = [float(c["high"]) for c in values][::-1]
        lows = [float(c["low"]) for c in values][::-1]

        return closes, highs, lows

    except Exception as e:
        print("ERROR:", e)
        return None

# ======================
# INDICATORS
# ======================
def ema(data, period):
    if len(data) < period:
        return data[-1]
    return np.convolve(data, np.ones(period)/period, mode='valid')[-1]

def rsi(data, period=14):
    if len(data) < period + 1:
        return 50

    deltas = np.diff(data)
    gain = np.maximum(deltas, 0)
    loss = np.abs(np.minimum(deltas, 0))

    avg_gain = np.mean(gain[:period])
    avg_loss = np.mean(loss[:period])

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ======================
# ANALYZE
# ======================
@app.get("/analyze")
def analyze(symbol: str):

    data = get_data(symbol)

    if not data:
        return {
            "symbol": symbol,
            "error": "No price data (check symbol or API key)"
        }

    closes, highs, lows = data
    price = closes[-1]

    ema50 = ema(closes, 50)
    ema200 = ema(closes, 100)
    rsi_val = rsi(closes)

    last_high = max(highs[-10:])
    last_low = min(lows[-10:])

    # ======================
    # SCORE SYSTEM
    # ======================
    score = 0

    # Trend
    if price > ema50 > ema200:
        score += 2
    elif price < ema50 < ema200:
        score -= 2

    # RSI
    if rsi_val > 55:
        score += 1
    elif rsi_val < 45:
        score -= 1

    # Structure
    if price >= last_high * 0.995:
        score -= 1
    elif price <= last_low * 1.005:
        score += 1

    # ======================
    # ALWAYS TRADE
    # ======================
    if score >= 0:
        bias = "BUY"
        sl = last_low
        tp = price + (price - sl) * 2
    else:
        bias = "SELL"
        sl = last_high
        tp = price - (sl - price) * 2

    # ======================
    # CONFIDENCE
    # ======================
    confidence = min(50 + abs(score) * 12, 95)

    # ======================
    # STRENGTH
    # ======================
    if confidence >= 80:
        strength = "STRONG"
    elif confidence >= 65:
        strength = "MEDIUM"
    else:
        strength = "WEAK"

    # ======================
    # RESPONSE
    # ======================
    return {
        "symbol": symbol.upper(),
        "price": round(price, 2),
        "bias": bias,
        "strength": strength,
        "confidence": round(confidence, 1),
        "entry": round(price, 2),
        "stop_loss": round(sl, 2),
        "take_profit": round(tp, 2),
        "ema50": round(ema50, 2),
        "ema200": round(ema200, 2),
        "rsi": round(rsi_val, 2)
    }
