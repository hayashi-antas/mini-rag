from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import chromadb
from openai import OpenAI

from .config import SETTINGS


@dataclass
class Reference:
    source: str
    chunk: int
    distance: float


@dataclass
class ChatResult:
    answer: str
    references: list[Reference]


@dataclass
class StreamChunk:
    """ストリーミング用のチャンク"""
    type: str  # 'token' or 'references'
    content: str = ""
    references: list[Reference] = None


def ask_question_stream(question: str) -> Iterator[StreamChunk]:
    """質問に対してRAG検索して回答をストリーミング生成する"""
    client = OpenAI(api_key=SETTINGS.openai_api_key)

    chroma = chromadb.PersistentClient(path=SETTINGS.chroma_dir)
    col = chroma.get_or_create_collection(name=SETTINGS.collection)

    # Embedding生成
    qvec = client.embeddings.create(
        model=SETTINGS.embed_model,
        input=question,
    ).data[0].embedding

    # ベクトル検索
    res = col.query(
        query_embeddings=[qvec],
        n_results=SETTINGS.top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = res["documents"][0]
    metas = res["metadatas"][0]
    distances = res["distances"][0]

    if not docs:
        yield StreamChunk(type='token', content="申し訳ございません。関連する資料が見つかりませんでした。")
        return

    # コンテキスト構築
    context_blocks = []
    for d, m in zip(docs, metas):
        context_blocks.append(f"[source={m['source']} chunk={m['chunk']}]\n{d}")

    context = "\n\n---\n\n".join(context_blocks)

    # LLMで回答生成（ストリーミング）
    prompt = f"""あなたは社内業務マニュアル検索アシスタントです。
必ず提供されたCONTEXTに基づいて答えてください。
CONTEXTに根拠がないことは「資料からは判断できません」と言ってください。

CONTEXT:
{context}

QUESTION:
{question}
"""

    stream = client.chat.completions.create(
        model=SETTINGS.llm_model,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )

    # ストリーミングでトークンを返す
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield StreamChunk(type='token', content=chunk.choices[0].delta.content)

    # 最後に参照情報を返す
    seen = set()
    unique_references = []
    for m, dist in zip(metas, distances):
        key = (m["source"], int(m["chunk"]))
        if key not in seen:
            seen.add(key)
            unique_references.append(
                Reference(
                    source=m["source"],
                    chunk=int(m["chunk"]),
                    distance=float(dist),
                )
            )

    yield StreamChunk(type='references', references=unique_references)


def ask_question(question: str) -> ChatResult:
    """質問に対してRAG検索して回答を生成する"""
    client = OpenAI(api_key=SETTINGS.openai_api_key)

    chroma = chromadb.PersistentClient(path=SETTINGS.chroma_dir)
    col = chroma.get_or_create_collection(name=SETTINGS.collection)

    # Embedding生成
    qvec = client.embeddings.create(
        model=SETTINGS.embed_model,
        input=question,
    ).data[0].embedding

    # ベクトル検索
    res = col.query(
        query_embeddings=[qvec],
        n_results=SETTINGS.top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = res["documents"][0]
    metas = res["metadatas"][0]
    distances = res["distances"][0]

    if not docs:
        return ChatResult(
            answer="申し訳ございません。関連する資料が見つかりませんでした。",
            references=[],
        )

    # コンテキスト構築
    context_blocks = []
    for d, m in zip(docs, metas):
        context_blocks.append(f"[source={m['source']} chunk={m['chunk']}]\n{d}")

    context = "\n\n---\n\n".join(context_blocks)

    # LLMで回答生成
    prompt = f"""あなたは社内業務マニュアル検索アシスタントです。
必ず提供されたCONTEXTに基づいて答えてください。
CONTEXTに根拠がないことは「資料からは判断できません」と言ってください。

CONTEXT:
{context}

QUESTION:
{question}
"""

    resp = client.chat.completions.create(
        model=SETTINGS.llm_model,
        messages=[{"role": "user", "content": prompt}],
    )

    answer = (resp.choices[0].message.content or "").strip()

    # 参照情報を整形（重複除去）
    seen = set()
    unique_references = []
    for m, dist in zip(metas, distances):
        key = (m["source"], int(m["chunk"]))
        if key not in seen:
            seen.add(key)
            unique_references.append(
                Reference(
                    source=m["source"],
                    chunk=int(m["chunk"]),
                    distance=float(dist),
                )
            )

    return ChatResult(answer=answer, references=unique_references)
