"""
Central configuration for the AUTOSAR HLD Document Analysis Assistant.

Reads settings from environment variables (.env file) so the API key
and model can be swapped without touching any code.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Project metadata
# ---------------------------------------------------------------------------
PROJECT_TITLE = "AUTOSAR HLD Document Analysis Assistant"
PROJECT_SUBTITLE = "Case Study 1 | Automotive Engineering AI"
VERSION = "2.0.0"

# ---------------------------------------------------------------------------
# Groq / LLM settings
# ---------------------------------------------------------------------------
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
# Handle potential missing openai/ prefix in env
if GROQ_MODEL in ("gpt-oss-120b", "gptoss120b", "gptoss120"):
    GROQ_MODEL = "openai/gpt-oss-120b"
elif GROQ_MODEL in ("gpt-oss-20b", "gptoss20b", "gptoss20"):
    GROQ_MODEL = "openai/gpt-oss-20b"

LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))

# ---------------------------------------------------------------------------
# Embedding settings
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")
EMBEDDING_DIM: int = 384  # matches bge-small-en-v1.5

# ---------------------------------------------------------------------------
# Chunking settings
# ---------------------------------------------------------------------------
CHUNK_SIZE_CHARS: int = int(os.getenv("CHUNK_SIZE_CHARS", "1200"))
CHUNK_OVERLAP_CHARS: int = int(os.getenv("CHUNK_OVERLAP_CHARS", "200"))
TOP_K_RETRIEVAL: int = int(os.getenv("TOP_K_RETRIEVAL", "6"))

# ---------------------------------------------------------------------------
# Upload limits
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
ALLOWED_EXTENSIONS: list = [".pdf"]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
EXPORT_DIR = DATA_DIR / "exports"
AUDIT_DB_PATH = DATA_DIR / "audit_log.db"
SAMPLE_DOCS_DIR = BASE_DIR / "sample_docs"
PROMPTS_DIR = BASE_DIR / "Model_Prompts_Config"

for d in (UPLOAD_DIR, VECTOR_STORE_DIR, EXPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)
