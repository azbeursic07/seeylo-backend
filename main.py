from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import openai

app = FastAPI()

# ===== CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== API KEYS =====
openai.api_key = os.getenv("OPENAI_API_KEY")
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")

# ===== SIMPLE STORAGE =====
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

# ===== GET PRICE =====
def get_price(symbol):
    url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_API_KEY}"
    res = requests.get(url).json()

    if "price" not in res:
        return None

    return float(res["price"])

# ===== CHECK TRADES =====
def check_trades():
    global user_balance

    for trade in active_trades:
        if trade["status"] != "open":
            continue

        price = get_price(trade["symbol"])
        if price is None:
            continue

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

# ===== HOME =====
@app.get("/")
def home():
    return {"status": "running"}

# ===== ANALYZE =====
@app.get("/analyze")
def analyze(symbol: str):

    symbol = normalize_symbol(symbol)

    price = get_price(symbol)

    if price is None:
        return {"error": "No price data"}

    prompt = f"""
Give a scalping trade idea for {symbol}.

Current price: {price}

Return:

Bias: Buy or Sell
Entry:
Stop Loss:
Take Profit:
Reason:
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response["choices"][0]["message"]["content"]

        # ===== SAVE TRADE (simple) =====
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
            "analysis": result
        }

    except Exception as e:
        return {"error": str(e)}

# ===== STATUS =====
@app.get("/status")
def status():
    check_trades()

    return {
        "balance": user_balance,
        "active_trades": active_trades,
        "history": trade_history
    }
