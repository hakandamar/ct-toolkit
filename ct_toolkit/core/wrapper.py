"""
ct_toolkit.core.wrapper
------------------------
TheseusWrapper: A proxy wrapping the existing LLM API client.

User only changes 2 lines:

    # Before
    client = openai.OpenAI()

    # After
    client = TheseusWrapper(openai.OpenAI())

In the background:
  1. Constitutional Kernel is injected into the system prompt.
  2. Each request/response is written to the Provenance Log with HMAC signature.
  3. Embedding cosine similarity (L1 ECS) is calculated.
  4. If the threshold is exceeded, L2/L3 is triggered.
"""
from __future__ import annotations

import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from ct_toolkit.core.kernel import ConstitutionalKernel
from ct_toolkit.core.compatibility import CompatibilityLayer, CompatibilityResult
from ct_toolkit.core.exceptions import CTToolkitError
from ct_toolkit.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WrapperConfig:
    """TheseusWrapper configuration."""
    kernel_path: str | Path | None = None
    template: str = "general"
    kernel_name: str = "default"
    divergence_l1_threshold: float = 0.15   # ECS — warning
    divergence_l2_threshold: float = 0.30   # Trigger LLM-as-judge
    divergence_l3_threshold: float = 0.50   # Trigger ICM battery
    vault_type: str = "local"               # "local" | "cloud"
    vault_path: str = "./ct_provenance.db"
    auto_inject_kernel: bool = True
    log_requests: bool = True
    judge_client: Any = None         # Separate provider client for L2/L3
    enterprise_mode: bool = False    # Run all tiers all the time


@dataclass
class CTResponse:
    """Enriched response returned by TheseusWrapper."""
    content: str
    provider: str
    model: str
    divergence_score: float | None = None
    divergence_tier: str | None = None      # "ok" | "l1_warning" | "l2_judge" | "l3_icm"
    provenance_id: str | None = None
    raw_response: Any = field(default=None, repr=False)

    def __str__(self) -> str:
        return self.content


class TheseusWrapper:
    """
    Identity-continuity proxy wrapping the LLM API client.

    Supported providers: openai, anthropic, ollama

    Usage:
        import openai
        from ct_toolkit import TheseusWrapper

        client = TheseusWrapper(openai.OpenAI())
        response = client.chat("Hello, how can I help you?")
        print(response.content)
        print(response.divergence_score)
    """

    def __init__(
        self,
        client: Any,
        config: WrapperConfig | None = None,
        *,
        kernel_path: str | Path | None = None,
        template: str = "general",
        kernel_name: str = "default",
    ) -> None:
        self._client = client
        self._config = config or WrapperConfig(
            kernel_path=kernel_path,
            template=template,
            kernel_name=kernel_name,
        )
        self._provider = self._detect_provider(client)
        self._kernel = self._load_kernel()
        self._compatibility: CompatibilityResult = CompatibilityLayer.check(
            template=self._config.template,
            kernel=self._config.kernel_name,
        )
        self._provenance_log = self._init_provenance_log()
        self._identity_layer = self._init_identity_layer()
        self._divergence_engine = self._init_divergence_engine()

        self._log_init()

    # ── Factory / Init ─────────────────────────────────────────────────────────

    def _detect_provider(self, client: Any) -> str:
        module = type(client).__module__
        if "openai" in module:
            return "openai"
        elif "anthropic" in module:
            return "anthropic"
        elif "ollama" in module:
            return "ollama"
        else:
            logger.warning(f"Unknown provider module: {module}. Marked as 'unknown'.")
            return "unknown"

    def _load_kernel(self) -> ConstitutionalKernel:
        if self._config.kernel_path:
            return ConstitutionalKernel.from_yaml(self._config.kernel_path)
        # Load built-in kernel
        kernel_path = (
            Path(__file__).parent.parent
            / "kernels"
            / f"{self._config.kernel_name}.yaml"
        )
        if kernel_path.exists():
            return ConstitutionalKernel.from_yaml(kernel_path)
        logger.warning(
            f"Kernel '{self._config.kernel_name}' not found, using default."
        )
        return ConstitutionalKernel.default()

    def _init_provenance_log(self) -> Any:
        """Initializes the Provenance Log vault adapter (Will be fully implemented in Step 2)."""
        from ct_toolkit.provenance.log import ProvenanceLog
        return ProvenanceLog(
            vault_type=self._config.vault_type,
            vault_path=self._config.vault_path,
        )

    def _init_identity_layer(self) -> Any:
        """Initializes the Identity Embedding Layer."""
        from ct_toolkit.identity.embedding import IdentityEmbeddingLayer
        return IdentityEmbeddingLayer(
            template=self._config.template,
        )

    def _init_divergence_engine(self) -> Any:
        """Initializes the Divergence Engine (judge_client is required for L2/L3)."""
        from ct_toolkit.divergence.engine import DivergenceEngine
        return DivergenceEngine(
            identity_layer=self._identity_layer,
            kernel=self._kernel,
            template=self._config.template,
            provider=self._provider if self._config.judge_client else None,
            judge_client=self._config.judge_client,
            l1_threshold=self._config.divergence_l1_threshold,
            l2_threshold=self._config.divergence_l2_threshold,
            l3_threshold=self._config.divergence_l3_threshold,
            enterprise_mode=self._config.enterprise_mode,
        )

    def _log_init(self) -> None:
        compat_note = (
            f" [{self._compatibility.level.value}]"
            + (f" — {self._compatibility.notes}" if self._compatibility.notes else "")
        )
        logger.info(
            f"TheseusWrapper initialized | "
            f"provider={self._provider} | "
            f"kernel={self._kernel.name} | "
            f"template={self._config.template}"
            f"{compat_note}"
        )

    # ── Main Chat Interface ─────────────────────────────────────────────────────

    def chat(
        self,
        message: str,
        *,
        model: str | None = None,
        system: str | None = None,
        history: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> CTResponse:
        """
        Sends a single message, returning the response with identity protection.

        Args:
            message:  User message
            model:    Model to use (provider default is used)
            system:   Additional system prompt (appended to kernel)
            history:  Conversation history [{"role": ..., "content": ...}]
        """
        composed_system = self._compose_system_prompt(system)
        messages = self._build_messages(message, history, composed_system)

        start_time = time.monotonic()

        try:
            raw_response = self._call_provider(messages, model=model, **kwargs)
        except Exception as e:
            logger.error(f"Provider API error: {e}")
            raise

        elapsed = time.monotonic() - start_time
        content = self._extract_content(raw_response)
        model_used = self._extract_model(raw_response, model)

        # Divergence Engine (L1 -> L2 -> L3)
        div_result = self._run_divergence_engine(
            message=message,
            response=content,
        )

        # Provenance Log record
        provenance_id = None
        if self._config.log_requests:
            provenance_id = self._provenance_log.record(
                request_text=message,
                response_text=content,
                divergence_score=div_result.l1_score,
                metadata={
                    "provider": self._provider,
                    "model": model_used,
                    "elapsed_ms": round(elapsed * 1000, 2),
                    "tier": div_result.tier.value,
                    "template": self._config.template,
                    "kernel": self._kernel.name,
                },
            )

        return CTResponse(
            content=content,
            provider=self._provider,
            model=model_used,
            divergence_score=div_result.l1_score,
            divergence_tier=div_result.tier.value,
            provenance_id=provenance_id,
            raw_response=raw_response,
        )

    # ── Provider Dispatch ──────────────────────────────────────────────────────

    def _call_provider(
        self,
        messages: list[dict[str, str]],
        model: str | None,
        **kwargs: Any,
    ) -> Any:
        if self._provider == "openai":
            return self._call_openai(messages, model, **kwargs)
        elif self._provider == "anthropic":
            return self._call_anthropic(messages, model, **kwargs)
        elif self._provider == "ollama":
            return self._call_ollama(messages, model, **kwargs)
        else:
            raise CTToolkitError(f"Unsupported provider: {self._provider}")

    def _call_openai(self, messages: list[dict], model: str | None, **kwargs: Any) -> Any:
        return self._client.chat.completions.create(
            model=model or "gpt-4o-mini",
            messages=messages,
            **kwargs,
        )

    def _call_anthropic(self, messages: list[dict], model: str | None, **kwargs: Any) -> Any:
        # Anthropic requires the system message sent separately
        system_content = ""
        filtered = []
        for m in messages:
            if m["role"] == "system":
                system_content = m["content"]
            else:
                filtered.append(m)
        return self._client.messages.create(
            model=model or "claude-sonnet-4-20250514",
            max_tokens=kwargs.pop("max_tokens", 4096),
            system=system_content,
            messages=filtered,
            **kwargs,
        )

    def _call_ollama(self, messages: list[dict], model: str | None, **kwargs: Any) -> Any:
        return self._client.chat(
            model=model or "llama3",
            messages=messages,
            **kwargs,
        )

    # ── Helper Methods ──────────────────────────────────────────────────────

    def _compose_system_prompt(self, extra: str | None) -> str:
        kernel_injection = self._kernel.get_system_prompt_injection()
        if extra:
            return f"{kernel_injection}\n{extra}"
        return kernel_injection

    def _build_messages(
        self,
        message: str,
        history: list[dict[str, str]] | None,
        system: str,
    ) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": message})
        return messages

    def _extract_content(self, raw: Any) -> str:
        # OpenAI
        if hasattr(raw, "choices"):
            return raw.choices[0].message.content or ""
        # Anthropic
        if hasattr(raw, "content") and isinstance(raw.content, list):
            return raw.content[0].text if raw.content else ""
        # Ollama
        if hasattr(raw, "message"):
            return raw.message.content or ""
        return str(raw)

    def _extract_model(self, raw: Any, fallback: str | None) -> str:
        if hasattr(raw, "model"):
            return raw.model
        return fallback or "unknown"

    def _run_divergence_engine(self, message: str, response: str) -> Any:
        """Runs the staged divergence engine (L1 -> L2 -> L3)."""
        try:
            return self._divergence_engine.analyze(message, response)
        except Exception as e:
            logger.error(f"Divergence Engine execution failed: {e}")
            from ct_toolkit.divergence.engine import DivergenceResult, DivergenceTier
            return DivergenceResult(
                tier=DivergenceTier.OK,
                summary=f"Engine execution failed: {e}"
            )

    # ── Kernel Management ────────────────────────────────────────────────────────

    def validate_user_rule(self, rule_text: str) -> None:
        """
        Validates a user-defined rule against the kernel.
        Raises an exception if there is a conflict.
        """
        self._kernel.validate_user_rule(rule_text)

    def endorse_rule(
        self,
        rule_text: str,
        operator_id: str = "unknown",
        approval_channel: Any = None,
        commitment_new_value: Any = None,
    ) -> Any:
        """
        Validates the rule; initiates the Reflective Endorsement
        flow if there is a plastic conflict. Throws hard reject on axiomatic violation.

        Args:
            rule_text:            The rule to be enforced
            operator_id:          The identity of the person granting approval
            approval_channel:     Custom approval channel (default: CLI)
            commitment_new_value: New value to assign to the commitment

        Returns: EndorsementRecord
        """
        from ct_toolkit.endorsement.reflective import ReflectiveEndorsement

        re = ReflectiveEndorsement(
            kernel=self._kernel,
            provenance_log=self._provenance_log,
            approval_channel=approval_channel,
        )
        return re.validate_and_endorse(
            rule_text=rule_text,
            operator_id=operator_id,
            commitment_new_value=commitment_new_value,
        )

    @property
    def kernel(self) -> ConstitutionalKernel:
        return self._kernel

    @property
    def compatibility(self) -> CompatibilityResult:
        return self._compatibility

    def __repr__(self) -> str:
        return (
            f"TheseusWrapper("
            f"provider={self._provider!r}, "
            f"kernel={self._kernel.name!r}, "
            f"template={self._config.template!r})"
        )