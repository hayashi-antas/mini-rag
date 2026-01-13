from __future__ import annotations

import glob
import os
import hashlib
from typing import Iterable

import chromadb
from openai import OpenAI

from .config import SETTINGS
from .chunking import chunk_text

def file_id(path: str) -> str:
    # 変更検知用に、パス+更新時刻でID作る（最小実装）
    st = os.stat(path)
    raw = f"{path}:{st.st_mtime_ns}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]

def read_docs() -> Iterable[tuple[str, str]]:
    for path in sorted(glob.glob("docs/*")):
        if os.path.isdir(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            yield path, f.read()

def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    # Embeddings API
    resp = client.embeddings.create(
        model=SETTINGS.embed_model,
        input=texts,
    )
    return [d.embedding for d in resp.data]

def main() -> None:
    client = OpenAI(api_key=SETTINGS.openai_api_key)

    chroma = chromadb.PersistentClient(path=SETTINGS.chroma_dir)
    col = chroma.get_or_create_collection(name=SETTINGS.collection)

    paths = list(read_docs())
    if not paths:
        print("docs/ にファイルがありません。まず docs/manual_1.md などを置いてください。")
        return

    all_texts = []
    all_ids = []
    all_metas = []

    for path, text in paths:
        chunks = chunk_text(text, chunk_size=SETTINGS.chunk_size, overlap=SETTINGS.chunk_overlap)
        base = file_id(path)

        for i, c in enumerate(chunks):
            cid = f"{base}:{i}"
            all_ids.append(cid)
            all_texts.append(c)
            all_metas.append({"source": path, "chunk": i})

    # 既存IDは先に消して入れ直す（最小実装）
    existing = set(col.get(ids=all_ids).get("ids", []))
    if existing:
        col.delete(ids=list(existing))

    vectors = embed_texts(client, all_texts)
    col.add(ids=all_ids, documents=all_texts, metadatas=all_metas, embeddings=vectors)

    print(f"✅ Ingest完了: files={len(paths)}, chunks={len(all_texts)}")
    print(f"   collection={SETTINGS.collection}, chroma_dir={SETTINGS.chroma_dir}")

if __name__ == "__main__":
    main()
