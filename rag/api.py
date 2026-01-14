from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from .chat_service import ask_question
from .ingest_service import run_ingest

app = FastAPI(title="mini-rag")

# テンプレート設定
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@app.get("/health")
async def health():
    """ヘルスチェック"""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """チャット画面"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/chat", response_class=HTMLResponse)
async def chat(request: Request, question: str = Form(...)):
    """
    チャット処理（HTMXから呼ばれる）
    HTML断片を返して会話ログに追記
    """
    try:
        result = ask_question(question)
        
        return templates.TemplateResponse(
            "chat_response.html",
            {
                "request": request,
                "question": question,
                "answer": result.answer,
                "references": result.references,
            },
        )
    except Exception as e:
        error_html = f"""
        <div class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p class="text-red-800 font-medium">❌ エラーが発生しました</p>
            <p class="text-red-600 text-sm mt-1">{str(e)}</p>
            <p class="text-red-500 text-xs mt-2">OpenAI API Keyが設定されているか、Chromaが初期化されているか確認してください。</p>
        </div>
        """
        return HTMLResponse(content=error_html)


@app.post("/ingest", response_class=HTMLResponse)
async def ingest(request: Request):
    """
    文書取り込み処理（HTMXから呼ばれる）
    """
    result = run_ingest()
    
    if result.success:
        message_html = f"""
        <div class="p-4 bg-green-50 border border-green-200 rounded-lg">
            <p class="text-green-800 font-medium">{result.message}</p>
            <p class="text-green-600 text-sm mt-1">docs/ 配下のファイルをベクトル化しました。</p>
        </div>
        """
    else:
        message_html = f"""
        <div class="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p class="text-red-800 font-medium">{result.message}</p>
        </div>
        """
    
    return HTMLResponse(content=message_html)
