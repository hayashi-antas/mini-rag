# mini-rag

ローカル環境で動作する **最小構成の RAG（Retrieval Augmented Generation）** サンプルです。

- Markdown 文書をベクトル化して保存
- 質問時に意味検索（RAG）
- 根拠（参照元）付きで LLM が回答

という一連の流れを、**AWS に載せ替え可能な構成**で実装しています。

---

## 特徴

- OpenAI API を利用した Embedding / 回答生成
- ChromaDB によるローカルベクトル検索
- Markdown 文書を対象とした RAG
- 回答時に参照元（source / chunk）を表示
- 秘密情報と設定情報を分離した設計
- 1Password CLI を用いた安全な秘密情報管理
- Makefile による簡潔な実行インターフェース
- 文書ハッシュによる差分 ingest（更新分のみ再Embedding）

---

## ディレクトリ構成

```text
mini-rag/
├── docs/                  # RAG対象の文書（Markdown）
├── rag/
│   ├── config.py          # 設定の読み込み
│   ├── chunking.py        # 文書分割ロジック
│   ├── ingest.py          # 文書 → Embedding → Chroma保存
│   └── chat.py            # 質問 → 検索 → 回答
├── config.env              # 設定値（Git管理OK）
├── secrets.env.tpl         # 秘密情報テンプレ（Git管理しない）
├── Makefile                # 実行用コマンド定義
├── requirements.txt
├── README.md
└── .gitignore
````

※ `.chroma/`（ベクトルDB）、`.venv/`、`.env` は Git 管理しません。

---

## 前提条件

* macOS / Linux
* Python 3.9+
* OpenAI API Key（Billing 有効）
* 1Password CLI（サインイン済み）

---

## 設計方針（重要）

### 秘密情報と設定情報を分離しています

#### 秘密情報（Secrets）

* `.env` ファイルに値を直接記入しない
* ローカル / CI / 本番で同一の運用を想定
* AI Agent やツールがファイルを読むことを前提とし、
  実行時に 1Password CLI 経由で環境変数として注入する


#### 設定情報（Config）

* モデル名
* チャンクサイズ
* Top-K などの検索パラメータ
* **Git 管理してOK**

この分離により、

* セキュリティ事故を防止
* AWS 移行時に Secrets Manager / Parameter Store へ自然に対応できる構成になっています。

---

## セットアップ

### 1. Python 仮想環境の作成

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
```

### 2. 依存ライブラリのインストール

```bash
pip install -r requirements.txt
```

---

## 設定ファイル

### config.env（Git管理OK）

```env
LLM_MODEL=gpt-4.1-mini
EMBED_MODEL=text-embedding-3-small
CHROMA_DIR=.chroma
COLLECTION=manuals
TOP_K=4
CHUNK_SIZE=800
CHUNK_OVERLAP=120
```

### secrets.env.tpl（Git管理しない）

```env
OPENAI_API_KEY=op://<vault名>/<item名>/<フィールド名>
```

※ 実行時に `op run` で環境変数として注入します。

---

## 使い方（Makefile 経由・推奨）

### 1. RAG 対象文書を追加

`docs/` 配下に Markdown ファイルを配置します。

```text
docs/
├── 01_kintai.md
├── 02_expense.md
├── 03_incident.md
└── ...
```

---

### 2. 文書を取り込む（Embedding & 保存）

```bash
make ingest
```

このコマンドは 差分 ingest として動作します。
- 新規ファイル：Embedding して追加
- 更新ファイル：該当ファイルのみ再Embedding
- 未変更ファイル：スキップ（再Embeddingなし）
- 削除ファイル：ベクトルDBから削除
これにより、文書量が増えても Embedding コストを最小限に抑えられる設計になっています。

成功すると、ローカルに `.chroma/` ディレクトリが作成されます。

---

### 3. チャットを起動

```bash
make chat
```

実行例：

```text
> 障害が発生したときはどうしたらいいでしょうか？

障害が発生したときは、まず最初の5分間で以下を必ず行います。

1. 「お客さま影響」を1行で書く  
2. 監視の赤いものをスクリーンショットする  
3. 直近のデプロイ内容を確認する（誰が、いつ、何をデプロイしたか）

また、重大障害（SEV1）の場合は、#incident-warroom を立てて連絡します。  
SEV1の定義は、主要機能が停止、売上に直撃、または全社が仕事できない状態です。

深夜（23:00～翌6:00）対応の場合は「INC」として扱い、タクシー利用が許可されます。

（以上は障害対応ランブックの内容によります）

--- references ---
- docs/03_incident.md (chunk 0)
- docs/03_incident.md (chunk 0)
- docs/manual_1.md (chunk 0)
- docs/manual_1.md (chunk 0)
```

---

## 注意事項

* `.chroma` はローカルのベクトルDBです（Git管理しません）
* 文書を変更した場合は **必ず再 ingest**
* ChatGPT Plus 契約とは別に OpenAI API 利用料が発生します

---

## 今後の拡張アイデア

* FastAPI 化して HTTP API にする
* Pinecone / pgvector への差し替え
* AWS（ECS / Lambda）へのデプロイ
* 文書更新時の差分 ingest

---

## 目的

* RAG の基本構造を理解する
* LLM を「業務システムの一部」として扱う練習
* AWS 実践研修への前段準備


