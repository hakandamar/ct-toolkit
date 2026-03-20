"""
ct_toolkit.core.compression_guard
---------------------------------
Provider-agnostic compression drift detector.
Works with OpenAI compaction, Anthropic compaction, LangChain memory,
or any framework that silently shortens context.
"""
from __future__ import annotations

from typing import Any, Dict, List, TYPE_CHECKING
from ct_toolkit.utils.logger import get_logger

if TYPE_CHECKING:
    from ct_toolkit.core.wrapper import TheseusWrapper

logger = get_logger(__name__)

class ContextCompressionGuard:
    """
    Guardrails for identity-preservation during context compression (summarization).
    """
    def __init__(self, wrapper: TheseusWrapper, threshold: float = 0.85) -> None:
        self.wrapper = wrapper
        self.threshold = threshold

    def analyze_summary_drift(
        self, 
        original_messages: List[Dict[str, str]] | str, 
        summary_text: str
    ) -> Dict[str, Any]:
        """
        Compares the identity embedding of original messages against the summary.
        Records the event in Provenance Log.
        
        Returns:
            Dict containing similarity score and drift status.
        """
        # 1. Flatten original messages into a single identity string if it's a list
        if isinstance(original_messages, list):
            original_text = " ".join([m.get("content", "") for m in original_messages])
        else:
            original_text = original_messages
            
        # 2. Compute embeddings via identity layer
        original_emb = self.wrapper._identity_layer._compute_vector(original_text)
        summary_emb = self.wrapper._identity_layer._compute_vector(summary_text)
        
        # 3. Calculate similarity (L1 ECS style)
        from ct_toolkit.identity.embedding import IdentityEmbeddingLayer
        similarity = IdentityEmbeddingLayer.calculate_similarity(original_emb, summary_emb)
        
        # 4. Identity Safety Floor (Internal protection against manipulated thresholds)
        drift_detected = similarity < self.threshold
        is_critical = similarity < 0.70  # A hard floor for identity integrity
        
        result = {
            "similarity": similarity,
            "threshold": self.threshold,
            "drift_detected": drift_detected,
            "critical_drift": is_critical,
            "event": "context_compression"
        }

        # 5. Record to Provenance Log (Tamper-proof record)
        if self.wrapper._config.log_requests:
            self.wrapper._provenance_log.record(
                request_text=f"[SYSTEM_ACTION: CONTEXT_SUMMARIZATION] History: {original_text[:500]}...",
                response_text=summary_text,
                divergence_score=1.0 - similarity,
                metadata={
                    "type": "compression_audit",
                    "similarity": similarity,
                    "threshold_applied": self.threshold,
                    "is_critical": is_critical,
                    "drift_flag": drift_detected,
                    "template": self.wrapper._config.template,
                    "kernel": self.wrapper.kernel.name,
                }
            )

        # 6. Trigger alert if detected (User action required)
        if (drift_detected or is_critical) and self.wrapper._config.drift_alert_callback:
            logger.warning(
                f"CT Toolkit | Identity Drift during compression: similarity={similarity:.2f} "
                f"(Threshold: {self.threshold}, Critical: {is_critical})"
            )
            self.wrapper._config.drift_alert_callback(result)

        return result

    def on_passive_detection(self, original: List[Dict[str, str]], compressed: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Triggered when TheseusWrapper detects a significant history shrinkage.
        """
        logger.info("CT Toolkit | Passive compression detection triggered.")
        original_text = " ".join(m.get("content", "") for m in original)
        compressed_text = " ".join(m.get("content", "") for m in compressed)
        return self.analyze_summary_drift(original_text, compressed_text)
