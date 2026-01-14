from __future__ import annotations

from dataclasses import dataclass

from .ingest import main as ingest_main


@dataclass
class IngestResult:
    success: bool
    message: str
    files_total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    chunks_written: int = 0


def run_ingest() -> IngestResult:
    """ingest処理を実行して結果を返す"""
    try:
        # 既存のingest.main()を呼び出す
        # TODO: より詳細な結果を返せるようingest.pyを改修することも検討
        ingest_main()
        return IngestResult(
            success=True,
            message="✅ Ingest完了しました",
        )
    except FileNotFoundError as e:
        return IngestResult(
            success=False,
            message=f"❌ ファイルが見つかりません: {e}",
        )
    except Exception as e:
        return IngestResult(
            success=False,
            message=f"❌ Ingest失敗: {e}",
        )
