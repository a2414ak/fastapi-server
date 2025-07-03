from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import logging

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 必要に応じて制限可能
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/claude")
async def call_claude(request: Request):
    body = await request.json()
    message = body.get("message")

    # ログ出力
    logging.info(f"📨 Claudeに送るメッセージ: {message}")

    headers = {
        "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
        "content-type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": "claude-3-opus-20240229",
        "messages": [{"role": "user", "content": message}],
        "max_tokens": 1000
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload
        )

        #API呼び出し結果のログ
        logging.info(f"📩 Claude応答ステータス: {response.status_code}")
        logging.info(f"📦 Claude応答内容: {result}")

        result = response.json()
        
        return result
    
