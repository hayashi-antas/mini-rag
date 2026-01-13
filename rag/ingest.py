from __future__ import annotations

import glob
import os
import hashlib
from collections import defaultdict
from typing import Iterable

import chromadb
from openai import OpenAI

from .config import SETTINGS
from .chunking import chunk_text


def read_docs() -> Iterable[tuple[str, str]]:
    for path in sorted(glob.glob("docs/*")):
        if os.path.isdir(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            yield path, f.read()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_source_id(path: str) -> str:
    # pathベースで安定するID（ファイル内容の変更では変わらない）
    return hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]


def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(
        model=SETTINGS.embed_model,
        input=texts,
    )
    return [d.embedding for d in resp.data]


def main() -> None:
    client = OpenAI(api_key=SETTINGS.openai_api_key)

    chroma = chromadb.PersistentClient(path=SETTINGS.chroma_dir)
    col = chroma.get_or_create_collection(name=SETTINGS.collection)

    # --- 現在のdocsを読み込む ---
    current_docs = list(read_docs())
    current_paths = {p for p, _ in current_docs}

    if not current_docs:
        print("docs/ にファイルがありません。まず docs/ にMarkdown等を置いてください。")
        return

    # --- DB側の既存エントリを取得し、sourceごとに状態を集約 ---
    # Chromaの全件取得（小規模前提の最小実装）
    existing = col.get(include=["metadatas"])
    existing_metas = existing.get("metadatas") or []
    existing_ids = existing.get("ids") or []

    db_sources: dict[str, dict[str, str]] = {}  # source -> {"file_hash": "..."}
    ids_by_source: dict[str, list[str]] = defaultdict(list)

    for _id, meta in zip(existing_ids, existing_metas):
        if not meta:
            continue
        src = meta.get("source")
        if not src:
            continue
        ids_by_source[src].append(_id)
        # 同一sourceのfile_hashは同じ想定。最初に見つけたものを採用
        if src not in db_sources and meta.get("file_hash"):
            db_sources[src] = {"file_hash": meta["file_hash"]}

    # --- 削除されたファイルをDBから削除 ---
    deleted_sources = sorted(set(db_sources.keys()) - current_paths)
    for src in deleted_sources:
        # source一致のものを全削除
        col.delete(where={"source": src})
    if deleted_sources:
        print(f"🧹 Deleted from DB (missing files): {len(deleted_sources)}")
        for s in deleted_sources:
            print(f"  - {s}")

    # --- 差分判定して、必要なものだけ再取り込み ---
    add_ids: list[str] = []
    add_texts: list[str] = []
    add_metas: list[dict] = []

    skipped = 0
    updated = 0
    created = 0

    for path, text in current_docs:
        file_hash = sha256_text(text)
        prev_hash = db_sources.get(path, {}).get("file_hash")

        if prev_hash == file_hash:
            skipped += 1
            continue

        # 変更 or 新規：古いチャンクを削除して入れ直し
        if prev_hash is None:
            created += 1
        else:
            updated += 1
            col.delete(where={"source": path})

        chunks = chunk_text(text, chunk_size=SETTINGS.chunk_size, overlap=SETTINGS.chunk_overlap)
        base = stable_source_id(path)

        for i, c in enumerate(chunks):
            cid = f"{base}:{i}"
            add_ids.append(cid)
            add_texts.append(c)
            add_metas.append({"source": path, "chunk": i, "file_hash": file_hash})

    if add_texts:
        vectors = embed_texts(client, add_texts)
        col.add(ids=add_ids, documents=add_texts, metadatas=add_metas, embeddings=vectors)

    total_files = len(current_docs)
    total_chunks = len(add_texts)

    print("✅ Delta ingest 完了")
    print(f"   files_total={total_files}  created={created}  updated={updated}  skipped={skipped}")
    print(f"   chunks_written={total_chunks}")
    print(f"   collection={SETTINGS.collection}, chroma_dir={SETTINGS.chroma_dir}")


if __name__ == "__main__":
    main()
