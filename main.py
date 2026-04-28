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

        Format response EXACTLY like:

        Entry: ...
        Stop Loss: ...
        Take Profit: ...
        Risk/Reward: ...
        Confidence: ...
        """

        headers = {
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )

        response_json = res.json()

        # 🔥 DEBUG SAFE
        if "choices" not in response_json:
            return {
                "error": "OpenAI API error",
                "full_response": response_json
            }

        return {
            "result": response_json["choices"][0]["message"]["content"]
        }

    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def root():
    return {"status": "running"}

@app.get("/analyze")
def analyze(symbol: str):
    return ask_ai(symbol)
