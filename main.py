from fastapi import FastAPI
import requests
import os

app = FastAPI()

OPENAI_KEY = os.getenv("OPENAI_KEY")

def ask_ai(symbol):
    try:
        prompt = f"""
        You are an elite scalping trading assistant.

        Analyze {symbol} and give BEST possible setup.

        Only give trade if high quality.
        If not → say NO TRADE.

        Return:
        Entry
        Stop Loss
        Take Profit
        Risk/Reward
        Confidence
        """

        headers = {
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}]
        }

        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )

        return res.json()

    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def root():
    return {"status": "running"}

@app.get("/analyze")
def analyze(symbol: str):
    return ask_ai(symbol)
