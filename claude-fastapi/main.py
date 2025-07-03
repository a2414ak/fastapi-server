from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import logging
import json
from typing import Optional, Dict, Any

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="議事録分析API", description="Claude 3 Haikuを使用した議事録分析とアドバイス生成")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 必要に応じて制限可能
    allow_methods=["*"],
    allow_headers=["*"],
)

# リクエストモデル
class MinutesRequest(BaseModel):
    minutes_text: str
    meeting_type: Optional[str] = "定例会議"
    participants: Optional[str] = ""

class MinutesAnalysisResponse(BaseModel):
    meeting_summary: str
    key_decisions: list
    action_items: list
    unresolved_issues: list
    next_meeting_advice: Dict[str, Any]
    productivity_insights: str
    formatted_report: str

async def call_claude_api(messages: list, max_tokens: int = 2000) -> Dict[str, Any]:
    """Claude APIを呼び出す共通関数"""
    headers = {
        "x-api-key": os.getenv("ANTHROPIC_API_KEY"),
        "content-type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    body = {
        "model": "claude-3-haiku-20240307",
        "messages": messages,
        "max_tokens": max_tokens
    }
    
    logger.info(f"🔍 Claudeリクエスト: {body}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=body
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"📦 Claude応答受信完了")
            return result
    except Exception as e:
        logger.error(f"🛑 Claude API呼び出しでエラー: {e}")
        raise HTTPException(status_code=500, detail=f"Claude API 呼び出しに失敗しました: {str(e)}")

def extract_json_from_response(response_text: str) -> Dict[str, Any]:
    """Claude応答からJSONを抽出"""
    import re
    
    # JSONブロックを探す
    json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
    if json_match:
        json_text = json_match.group(1)
    else:
        # JSONブロックがない場合は { から } までを抽出
        brace_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if brace_match:
            json_text = brace_match.group(0)
        else:
            json_text = response_text
    
    try:
        return json.loads(json_text)
    except json.JSONDecodeError:
        # JSONパースに失敗した場合はテキストのまま返す
        return {"raw_response": response_text}

def generate_formatted_report(analysis_result: Dict[str, Any]) -> str:
    """分析結果から読みやすいレポートを生成"""
    if "raw_response" in analysis_result:
        return analysis_result["raw_response"]
    
    report = "# 議事録分析レポート\n\n"
    
    report += f"## 会議サマリー\n{analysis_result.get('meeting_summary', 'N/A')}\n\n"
    
    if analysis_result.get('key_decisions'):
        report += "## 主要な決定事項\n"
        for decision in analysis_result['key_decisions']:
            report += f"- {decision}\n"
        report += "\n"
    
    if analysis_result.get('action_items'):
        report += "## アクションアイテム\n"
        for item in analysis_result['action_items']:
            if isinstance(item, dict):
                report += f"- **{item.get('task', 'N/A')}**\n"
                report += f"  - 担当者: {item.get('assignee', 'N/A')}\n"
                report += f"  - 期限: {item.get('deadline', 'N/A')}\n\n"
            else:
                report += f"- {item}\n"
        report += "\n"
    
    if analysis_result.get('unresolved_issues'):
        report += "## 未解決課題\n"
        for issue in analysis_result['unresolved_issues']:
            report += f"- {issue}\n"
        report += "\n"
    
    next_advice = analysis_result.get('next_meeting_advice', {})
    if next_advice:
        report += "## 次回会議への提案\n"
        
        if next_advice.get('agenda_suggestions'):
            report += "### 議題提案\n"
            for agenda in next_advice['agenda_suggestions']:
                report += f"- {agenda}\n"
            report += "\n"
        
        if next_advice.get('preparation_items'):
            report += "### 事前準備事項\n"
            for prep in next_advice['preparation_items']:
                report += f"- {prep}\n"
            report += "\n"
        
        if next_advice.get('improvement_points'):
            report += "### 改善提案\n"
            for improvement in next_advice['improvement_points']:
                report += f"- {improvement}\n"
            report += "\n"
    
    if analysis_result.get('productivity_insights'):
        report += f"## 生産性に関する洞察\n{analysis_result['productivity_insights']}\n\n"
    
    return report



@app.post("/analyze-minutes", response_model=MinutesAnalysisResponse)
async def analyze_minutes(request: MinutesRequest):
    """議事録を分析して次回会議へのアドバイスを生成"""
    
    prompt = f"""
以下の議事録を分析し、次回の会議に向けた具体的なアドバイスを提供してください。

【会議種類】{request.meeting_type}
【参加者】{request.participants}

【議事録】
{request.minutes_text}

以下の観点から分析し、JSON形式で回答してください：

{{
    "meeting_summary": "会議の要点サマリー（2-3文で簡潔に）",
    "key_decisions": ["決定事項1", "決定事項2", ...],
    "action_items": [
        {{
            "task": "タスク内容",
            "assignee": "担当者",
            "deadline": "期限"
        }}
    ],
    "unresolved_issues": ["未解決課題1", "未解決課題2", ...],
    "next_meeting_advice": {{
        "agenda_suggestions": ["議題提案1", "議題提案2", ...],
        "preparation_items": ["準備事項1", "準備事項2", ...],
        "improvement_points": ["改善点1", "改善点2", ...]
    }},
    "productivity_insights": "会議の生産性に関する洞察とコメント"
}}

日本語で詳細かつ実用的な内容を提供してください。
必ずJSON形式で回答し、各項目を具体的に記載してください。
"""
    
    messages = [
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    # Claude API呼び出し
    claude_response = await call_claude_api(messages, 2000)
    
    # 応答からテキストを抽出
    response_text = claude_response.get("content", [{}])[0].get("text", "")
    
    # JSONを抽出してパース
    analysis_result = extract_json_from_response(response_text)
    
    # フォーマットされたレポートを生成
    formatted_report = generate_formatted_report(analysis_result)
    
    # レスポンス用にデータを整理
    if "raw_response" in analysis_result:
        # JSONパースに失敗した場合のフォールバック
        return MinutesAnalysisResponse(
            meeting_summary="分析結果の解析に失敗しました",
            key_decisions=[],
            action_items=[],
            unresolved_issues=[],
            next_meeting_advice={},
            productivity_insights="分析結果を正しく取得できませんでした",
            formatted_report=analysis_result["raw_response"]
        )
    
    return MinutesAnalysisResponse(
        meeting_summary=analysis_result.get("meeting_summary", ""),
        key_decisions=analysis_result.get("key_decisions", []),
        action_items=analysis_result.get("action_items", []),
        unresolved_issues=analysis_result.get("unresolved_issues", []),
        next_meeting_advice=analysis_result.get("next_meeting_advice", {}),
        productivity_insights=analysis_result.get("productivity_insights", ""),
        formatted_report=formatted_report
    )

@app.post("/quick-advice")
async def quick_meeting_advice(request: MinutesRequest):
    """簡易版：議事録から次回会議への簡単なアドバイスを生成"""
    
    prompt = f"""
以下の議事録を読んで、次回の会議で最も重要な3つのポイントを教えてください。

議事録：
{request.minutes_text}

以下の形式で簡潔に回答してください：
1. 【フォローアップが必要な項目】
2. 【次回までに準備すべき事項】
3. 【会議の改善提案】

各項目は1-2文で具体的に記載してください。
"""
    
    messages = [
        {
            "role": "user",
            "content": prompt
        }
    ]
    
    claude_response = await call_claude_api(messages, 1000)
    response_text = claude_response.get("content", [{}])[0].get("text", "")
    
    return {"advice": response_text}

@app.get("/")
async def root():
    """API情報を返す"""
    return {
        "message": "議事録分析API",
        "endpoints": {
            "/analyze-minutes": "詳細な議事録分析とアドバイス生成",
            "/quick-advice": "簡易版アドバイス生成"
        }
    }

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    return {
        "status": "healthy",
        "api_key_configured": bool(api_key)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)