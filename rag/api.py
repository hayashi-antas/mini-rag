from __future__ import annotations

import anyio
import json
from pathlib import Path

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from .chat_service import ask_question, ask_question_stream
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


@app.post("/chat/stream")
async def chat_stream(question: str = Form(...)):
    """
    チャット処理（ストリーミング版）
    Server-Sent Eventsでリアルタイムに回答を返す
    """
    async def event_generator():
        try:
            # 一部のプロキシ/ブラウザが小さなチャンクをバッファしないように、最初にコメントを送ってフラッシュする
            yield ":" + (" " * 2048) + "\n\n"
            await anyio.sleep(0)

            for chunk in ask_question_stream(question):
                if chunk.type == 'token':
                    # トークンを送信
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
                    await anyio.sleep(0)
                elif chunk.type == 'references':
                    # 参照情報を送信
                    refs = [
                        {
                            'source': ref.source,
                            'chunk': ref.chunk,
                            'distance': ref.distance,
                        }
                        for ref in chunk.references
                    ]
                    yield f"data: {json.dumps({'type': 'references', 'references': refs})}\n\n"
                    await anyio.sleep(0)
            
            # 完了を通知
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # nginx等のリバプロ配下でのバッファ抑止（ローカルでは無害）
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/debug/stream")
async def debug_stream():
    """ストリーミングの疎通確認用（OpenAI不要）"""
    async def event_generator():
        yield ":" + (" " * 2048) + "\n\n"
        await anyio.sleep(0)
        for token in ["ストリーミング", "できて", "います", "…", "\n", "OK"]:
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            await anyio.sleep(0.2)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
