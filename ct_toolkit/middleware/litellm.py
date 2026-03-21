"""
ct_toolkit.middleware.litellm
------------------------------
LiteLLM integration for identity-continuity guardrails.

Provides ``TheseusLiteLLMCallback`` which hooks into LiteLLM's CustomLogger
system to enforce Constitutional Kernel rules on every LLM call — regardless
of which provider or model is being used underneath.

This is the "Governance Proxy Middleware" pattern:
  - Works with ANY provider LiteLLM supports (100+ models)
  - No agent code changes required
  - Pre-call: kernel validation → blocks axiomatic violations
  - Post-call: divergence analysis + provenance logging

Optional dependency — requires ``pip install 'ct-toolkit[litellm]'``.
LiteLLM does NOT need to be installed for the rest of ct-toolkit to work.

## SDK usage (direct litellm calls)::

    import litellm
    from ct_toolkit import TheseusWrapper, WrapperConfig
    from ct_toolkit.middleware.litellm import TheseusLiteLLMCallback

    wrapper = TheseusWrapper(provider="openai", kernel_name="defense")
    handler = TheseusLiteLLMCallback(wrapper)

    litellm.callbacks = [handler]

    # All litellm.completion() calls are now identity-protected
    response = litellm.completion(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello!"}]
    )

## LiteLLM Proxy (proxy_config.yaml)::

    model_list:
      - model_name: gpt-4o-mini
        litellm_params:
          model: gpt-4o-mini

    litellm_settings:
      callbacks: ct_toolkit.middleware.litellm.proxy_handler_instance

Compatible with litellm >= 1.40.0
"""
from __future__ import annotations

import time
from typing import Any, Optional

from ct_toolkit.core.wrapper import TheseusWrapper, WrapperConfig
from ct_toolkit.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from litellm.integrations.custom_logger import CustomLogger
except ImportError as _exc:
    raise ImportError(
        "TheseusLiteLLMCallback requires litellm. "
        "Install with: pip install 'litellm'"
    ) from _exc


class TheseusLiteLLMCallback(CustomLogger):
    """
    LiteLLM CustomLogger that enforces CT-Toolkit identity guardrails.

    Hooks:
      async_pre_call_hook      → Kernel validation (blocks axiomatic violations)
      async_log_success_event  → Divergence engine + Provenance Log
      async_log_failure_event  → Failure logging
      log_success_event        → Sync fallback for non-async callers
    """

    def __init__(self, wrapper: TheseusWrapper) -> None:
        super().__init__()
        self.wrapper = wrapper
        logger.info(
            f"CT Toolkit | TheseusLiteLLMCallback initialized "
            f"(kernel='{wrapper.kernel.name}', template='{wrapper._config.template}')"
        )

    # ── Pre-call: Axiomatic Kernel Validation ─────────────────────────────────

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict,
        call_type: str,
    ) -> Optional[str]:
        """
        Runs BEFORE the LLM API call.
        Extracts user message and validates against Constitutional Kernel.

        Returns:
            None   → call proceeds normally
            str    → LiteLLM returns this string as the response (call blocked)
        """
        messages = data.get("messages", [])
        user_text = _extract_user_text(messages)

        if not user_text:
            return None

        try:
            self.wrapper.validate_user_rule(user_text)
            return None  # All good, proceed
        except Exception as e:
            logger.warning(
                f"CT Toolkit | LiteLLM pre-call kernel violation: {e} | "
                f"model={data.get('model', 'unknown')}"
            )
            # Return blocked message — LiteLLM formats this into a proper response
            return (
                f"[CT Toolkit BLOCKED] This request violates an identity constraint "
                f"and cannot be processed. Reason: {e}"
            )

    # ── Post-call: Divergence Analysis + Provenance ───────────────────────────

    async def async_log_success_event(
        self,
        kwargs: dict,
        response_obj: Any,
        start_time: float,
        end_time: float,
    ) -> None:
        """
        Runs AFTER a successful LLM call.
        Runs Divergence Engine and writes to Provenance Log.
        """
        try:
            messages = kwargs.get("messages", [])
            user_text = _extract_user_text(messages)
            response_text = _extract_response_text(response_obj)
            model = kwargs.get("model", "unknown")

            if not response_text:
                return

            # Interaction count for Elasticity Scheduler
            interaction_count = 0
            if self.wrapper._config.log_requests:
                interaction_count = self.wrapper._provenance_log.get_interaction_count(
                    template=self.wrapper._config.template,
                    kernel_name=self.wrapper.kernel.name,
                    model=model,
                )

            # Run Divergence Engine (L1 → L2 → L3)
            div_result = self.wrapper._run_divergence_engine(
                message=user_text,
                response=response_text,
                interaction_count=interaction_count,
            )

            if getattr(div_result, 'cascade_blocked', False):
                logger.warning(
                    f"CT Toolkit | cascade_blocked=True via LiteLLM callback. "
                    f"model={model} | score={div_result.l1_score:.4f} | "
                    f"Consider halting downstream agent calls."
                )

            # Provenance Log
            if self.wrapper._config.log_requests:
                elapsed_ms = (end_time - start_time) * 1000 if isinstance(start_time, float) else 0.0
                self.wrapper._provenance_log.record(
                    request_text=user_text or "[LiteLLM Interaction]",
                    response_text=response_text,
                    divergence_score=div_result.l1_score,
                    metadata={
                        "middleware": "litellm",
                        "provider": kwargs.get("custom_llm_provider", "unknown"),
                        "model": model,
                        "elapsed_ms": round(elapsed_ms, 2),
                        "tier": div_result.tier.value,
                        "cascade_blocked": getattr(div_result, 'cascade_blocked', False),
                        "template": self.wrapper._config.template,
                        "kernel": self.wrapper.kernel.name,
                    },
                )

            logger.debug(
                f"CT Toolkit | LiteLLM success | model={model} | "
                f"divergence={div_result.l1_score:.4f} | tier={div_result.tier.value}"
            )

        except Exception as e:
            # Never crash the caller — log and continue
            logger.error(f"CT Toolkit | LiteLLM callback error (success event): {e}")

    async def async_log_failure_event(
        self,
        kwargs: dict,
        response_obj: Any,
        start_time: float,
        end_time: float,
    ) -> None:
        """Logs LLM failures to provenance for audit trail completeness."""
        try:
            model = kwargs.get("model", "unknown")
            exception = kwargs.get("exception", "unknown error")
            logger.warning(f"CT Toolkit | LiteLLM failure | model={model} | error={exception}")

            if self.wrapper._config.log_requests:
                messages = kwargs.get("messages", [])
                self.wrapper._provenance_log.record(
                    request_text=_extract_user_text(messages) or "[LiteLLM Failed Interaction]",
                    response_text=f"[ERROR: {exception}]",
                    divergence_score=None,
                    metadata={
                        "middleware": "litellm",
                        "model": model,
                        "status": "failed",
                        "template": self.wrapper._config.template,
                        "kernel": self.wrapper.kernel.name,
                    },
                )
        except Exception as e:
            logger.error(f"CT Toolkit | LiteLLM callback error (failure event): {e}")

    # ── Sync fallback ─────────────────────────────────────────────────────────

    def log_success_event(
        self,
        kwargs: dict,
        response_obj: Any,
        start_time: float,
        end_time: float,
    ) -> None:
        """Sync fallback — runs divergence + provenance for non-async callers."""
        try:
            messages = kwargs.get("messages", [])
            user_text = _extract_user_text(messages)
            response_text = _extract_response_text(response_obj)
            model = kwargs.get("model", "unknown")

            if not response_text:
                return

            div_result = self.wrapper._run_divergence_engine(
                message=user_text,
                response=response_text,
            )

            if self.wrapper._config.log_requests:
                self.wrapper._provenance_log.record(
                    request_text=user_text or "[LiteLLM Interaction]",
                    response_text=response_text,
                    divergence_score=div_result.l1_score,
                    metadata={
                        "middleware": "litellm",
                        "model": model,
                        "tier": div_result.tier.value,
                        "template": self.wrapper._config.template,
                        "kernel": self.wrapper.kernel.name,
                    },
                )
        except Exception as e:
            logger.error(f"CT Toolkit | LiteLLM callback error (sync success): {e}")


# ── Proxy Mode: singleton instance for proxy_config.yaml ─────────────────────

def create_proxy_handler(
    kernel_name: str = "default",
    template: str = "general",
    vault_path: str = "./ct_provenance.db",
    enterprise_mode: bool = False,
) -> TheseusLiteLLMCallback:
    """
    Factory for LiteLLM Proxy mode.

    Usage in proxy_config.yaml::

        litellm_settings:
          callbacks: ct_toolkit.middleware.litellm.proxy_handler_instance

    Or with custom config::

        # custom_callbacks.py
        from ct_toolkit.middleware.litellm import create_proxy_handler
        proxy_handler_instance = create_proxy_handler(kernel_name="defense", template="defense")
    """
    wrapper = TheseusWrapper(
        provider="openai",  # Proxy doesn't need a specific provider
        config=WrapperConfig(
            kernel_name=kernel_name,
            template=template,
            vault_path=vault_path,
            enterprise_mode=enterprise_mode,
        ),
    )
    return TheseusLiteLLMCallback(wrapper)


# Default proxy singleton — works out-of-the-box for proxy_config.yaml
proxy_handler_instance = create_proxy_handler()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_user_text(messages: list[dict]) -> str:
    """Extract non-system message content from LiteLLM messages list."""
    parts = []
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") != "system":
            content = msg.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                # Handle multimodal content blocks
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))
    return " ".join(parts)


def _extract_response_text(response_obj: Any) -> str:
    """Extract text content from LiteLLM ModelResponse."""
    if response_obj is None:
        return ""
    try:
        # Standard LiteLLM ModelResponse
        if hasattr(response_obj, "choices"):
            if not response_obj.choices:
                return ""  # Empty choices list
            choice = response_obj.choices[0]
            if hasattr(choice, "message") and choice.message:
                return choice.message.content or ""
            if hasattr(choice, "text"):
                return choice.text or ""
        # Dict format
        if isinstance(response_obj, dict):
            choices = response_obj.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
    except Exception:
        pass
    return str(response_obj)
