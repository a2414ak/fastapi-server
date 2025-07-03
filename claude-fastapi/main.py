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
    data = await request.json()
    user_message = data.get("message")

    # Claude APIに渡す messages（JSON構造）
    if user_message.strip() == "テスト":
        messages = [
            {
                "role": "user",
                "content": "「test ok」とだけ返してください。"
            }
        ]
    else:
        messages = [
            {
                "role": "user",
                "content": f"""
                次の言葉を使って、面白いダジャレをひとつ作ってください：
                {user_message}
                ※ 返答は一文で、ダジャレのみ返してください。
                """
            }
        ]


    # APIリクエスト準備
    headers = {
        "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
        "content-type": "application/json",
        "anthropic-version": "2023-06-01"
    }

    body = {
        "model": "claude-3-haiku-20240307",
        "messages": messages,
        "max_tokens": 1000
    }

    # Claude呼び出し前にログを出す
    logging.info(f"🔍 Claudeリクエスト: {body}")
    logging.info(f"🔍 ヘッダー: {headers}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=body
            )
            response.raise_for_status()  # 4xx/5xx を例外に
            result = response.json()
            logging.info(f"📦 Claude応答内容: {result}")
            return result
    except Exception as e:
        logging.error(f"🛑 Claude API呼び出しでエラー: {e}")
        return {"error": "Claude API 呼び出しに失敗しました"}
