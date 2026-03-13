"""
ct_toolkit.identity.embedding
------------------------------
Identity Embedding Layer: Calculates cosine similarity with static reference 
embedding to produce L1 divergence score.

Step 3 MVP implementation:
  - Static reference vector is loaded from Template YAML
  - Each response embedding is calculated
  - Cosine distance = 1 - cosine_similarity → divergence score
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from ct_toolkit.utils.logger import get_logger

logger = get_logger(__name__)


class IdentityEmbeddingLayer:
    """
    Static reference embedding management and L1 divergence calculation.

    Embedding calculation strategy (MVP):
      If there is no provider API embedding endpoint, a simple TF-IDF like
      word vector is used. In Step 6, it will be migrated to real semantic 
      embedding using OpenAI/Anthropic embedding API.

    Usage:
        layer = IdentityEmbeddingLayer(template="medical")
        score = layer.compute_divergence("Response text here")
        # score: 0.0 (identical) → 1.0 (completely different)
    """

    def __init__(
        self,
        template: str = "general",
        embedding_client: Any = None,  # Provider client for real embeddings
        embedding_model: str = "text-embedding-3-small",
    ) -> None:
        self._template = template
        self._embedding_client = embedding_client
        self._embedding_model = embedding_model
        self._reference_vector: np.ndarray | None = None
        self._template_keywords: list[str] = []
        self._load_template()

    # ── Template Loading ───────────────────────────────────────────────────────

    def _load_template(self) -> None:
        template_path = (
            Path(__file__).parent
            / "templates"
            / f"{self._template}.yaml"
        )
        if not template_path.exists():
            logger.warning(
                f"Template '{self._template}' not found, using 'general'."
            )
            template_path = Path(__file__).parent / "templates" / "general.yaml"

        import yaml
        with open(template_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._template_keywords = data.get("identity_keywords", [])
        reference_text = data.get("reference_text", " ".join(self._template_keywords))
        self._reference_vector = self._compute_vector(reference_text)
        logger.info(
            f"Identity template loaded: '{self._template}' | "
            f"keywords={len(self._template_keywords)}"
        )

    # ── Divergence Calculation ──────────────────────────────────────────────────────

    def compute_divergence(self, text: str) -> float:
        """
        Calculates the divergence score of the given text against the static reference.

        Returns:
            0.0 → identical to reference (identity preserved)
            1.0 → completely different from reference (maximum divergence)
        """
        if self._reference_vector is None:
            logger.warning("No reference vector, divergence cannot be calculated.")
            return 0.0

        candidate_vector = self._compute_vector(text)
        similarity = self._cosine_similarity(self._reference_vector, candidate_vector)
        divergence = 1.0 - similarity

        return round(float(divergence), 6)

    def update_reference(self, new_text: str) -> None:
        """
        Updates the static reference vector.
        WARNING: This should only be called after Reflective Endorsement approval.
        """
        self._reference_vector = self._compute_vector(new_text)
        logger.info("Reference vector updated.")

    # ── Vector Calculation (MVP: keyword-based, Step 6: real embedding) ───────────

    def _compute_vector(self, text: str) -> np.ndarray:
        """
        Uses the embedding API if a client is available.
        Otherwise falls back to simple MVP keyword/ngram implementation.
        """
        if self._embedding_client is not None:
            try:
                response = self._embedding_client.embeddings.create(
                    input=[text],
                    model=self._embedding_model
                )
                embedding = response.data[0].embedding
                return np.array(embedding, dtype=np.float32)
            except Exception as e:
                logger.error(f"Embedding API failed, falling back to local method: {e}")
                # Fall through to local method
        if not self._template_keywords:
            # Fallback: character n-gram hash vector
            return self._ngram_hash_vector(text)

        text_lower = text.lower()
        vector = np.array(
            [float(text_lower.count(kw.lower())) for kw in self._template_keywords],
            dtype=np.float32,
        )
        # L2 normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector

    def _ngram_hash_vector(self, text: str, dim: int = 256) -> np.ndarray:
        """
        If no keywords: projects character 3-gram hashes into a dim-dimensional vector.
        Provider independent, zero-dependency fallback.
        """
        vector = np.zeros(dim, dtype=np.float32)
        words = text.lower().split()
        for word in words:
            for i in range(len(word) - 2):
                trigram = word[i:i+3]
                h = int(hashlib.md5(trigram.encode()).hexdigest(), 16) % dim
                vector[h] += 1.0
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        if a.shape != b.shape:
            # Safe fallback for dimension mismatch
            min_len = min(len(a), len(b))
            a, b = a[:min_len], b[:min_len]
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))
