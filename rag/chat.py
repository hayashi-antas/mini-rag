from __future__ import annotations

import chromadb
from openai import OpenAI

from .config import SETTINGS

def main() -> None:
    client = OpenAI(api_key=SETTINGS.openai_api_key)

    chroma = chromadb.PersistentClient(path=SETTINGS.chroma_dir)
    col = chroma.get_or_create_collection(name=SETTINGS.collection)

    print("RAGチャット（終了: Ctrl+C）")
    while True:
        q = input("\n> ").strip()
        if not q:
            continue

        qvec = client.embeddings.create(
            model=SETTINGS.embed_model,
            input=q,
        ).data[0].embedding

        res = col.query(
            query_embeddings=[qvec],
            n_results=SETTINGS.top_k,
            include=["documents", "metadatas", "distances"],
        )

        docs = res["documents"][0]
        metas = res["metadatas"][0]

        context_blocks = []
        for d, m in zip(docs, metas):
            context_blocks.append(f"[source={m['source']} chunk={m['chunk']}]\n{d}")

        context = "\n\n---\n\n".join(context_blocks)

        prompt = f"""あなたは社内業務マニュアル検索アシスタントです。
必ず提供されたCONTEXTに基づいて答えてください。
CONTEXTに根拠がないことは「資料からは判断できません」と言ってください。

CONTEXT:
{context}

QUESTION:
{q}
"""

        # Chat Completions API（標準）
        resp = client.chat.completions.create(
            model=SETTINGS.llm_model,
            messages=[{"role": "user", "content": prompt}],
        )

        print("\n" + (resp.choices[0].message.content or "").strip())

        print("\n--- references ---")
        for m in metas:
            print(f"- {m['source']} (chunk {m['chunk']})")

if __name__ == "__main__":
    main()
