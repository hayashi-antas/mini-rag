# mini-rag

ローカル環境で動作する最小構成のRAG（Retrieval Augmented Generation）サンプル。

## Features
- OpenAI API を使った Embedding / Chat
- Chroma によるローカルベクトル検索
- 社内マニュアル想定のRAG構成
- 秘密情報は 1Password CLI 経由で注入

## Setup
- Python 3.9+
- 1Password CLI
- OpenAI API Key（Billing 有効）

## Run
```bash
op run --env-file=secrets.env.tpl -- python -m rag.ingest
op run --env-file=secrets.env.tpl -- python -m rag.chat
```