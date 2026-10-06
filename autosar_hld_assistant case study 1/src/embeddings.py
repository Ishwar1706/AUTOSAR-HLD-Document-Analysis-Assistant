"""
Embedding module.

Wraps a local sentence-transformers model so text chunks can be converted
into vectors for semantic search. Runs entirely on-device (CPU is fine
for pilot-scale volumes) and needs no external API key.

First run requires internet to download the model (~130 MB); cached after that.
"""

import logging
from functools import lru_cache
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

import config

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load and cache the embedding model (loaded once per process)."""
    logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL_NAME}")
    try:
        model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
        logger.info("Embedding model loaded successfully.")
        return model
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        raise RuntimeError(
            f"Could not load embedding model '{config.EMBEDDING_MODEL_NAME}'. "
            "Ensure internet access on first run for model download. "
            f"Error: {e}"
        )


def embed_texts(texts: List[str]) -> np.ndarray:
    """
    Embed a list of strings and return an (N, dim) float32 numpy array,
    L2-normalized so inner-product search behaves like cosine similarity.
    """
    if not texts:
        return np.zeros((0, config.EMBEDDING_DIM), dtype="float32")

    model = get_embedding_model()
    vectors = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32,
    )
    return vectors.astype("float32")


def embed_query(query: str) -> np.ndarray:
    """Embed a single query string. Returns a (1, dim) array."""
    return embed_texts([query])


def get_model_info() -> dict:
    """Return information about the current embedding model."""
    return {
        "model_name": config.EMBEDDING_MODEL_NAME,
        "embedding_dim": config.EMBEDDING_DIM,
        "type": "sentence-transformers (local)",
        "requires_api_key": False,
    }
