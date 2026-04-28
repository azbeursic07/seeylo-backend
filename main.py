from fastapi import FastAPI
import requests
import os

app = FastAPI()

OPENAI_KEY = os.getenv("OPENAI_KEY")


def ask_ai(symbol):
    try:
        prompt = f"""
You are a professional scalping trader.

Analyze {symbol} for short-term trading (1m–15m).

Rules:
- Always provide a trade idea unless market is completely unclear
- Prefer high probability setups
- Use tight Stop Loss
- Minimum Risk/Reward = 1.5

Return EXACT format:

Bias: (Buy or Sell)
Entry: ...
Stop Loss: ...
Take Profit: ...
Risk/Reward: ...
Confidence: (1-100%)
Reason: (short explanation)
"""

        headers = {
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=15
        )

        response_json = res.json()

        # 🔥 Če OpenAI vrne error
        if "choices" not in response_json:
            return {
                "error": "OpenAI API error",
                "details": response_json
            }

        result_text = response_json["choices"][0]["message"]["content"]

        return {
            "result": result_text
        }

    except Exception as e:
        return {
            "error": str(e)
        }


@app.get("/")
def root():
    return {"status": "running"}


@app.get("/analyze")
def analyze(symbol: str):
    if not symbol:
        return {"error": "No symbol provided"}

    return ask_ai(symbol)
