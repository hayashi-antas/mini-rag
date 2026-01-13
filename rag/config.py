import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.environ["OPENAI_API_KEY"]
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4.1-mini")
    embed_model: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")
    chroma_dir: str = os.getenv("CHROMA_DIR", ".chroma")
    collection: str = os.getenv("COLLECTION", "manuals")
    top_k: int = int(os.getenv("TOP_K", "4"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))

SETTINGS = Settings()
