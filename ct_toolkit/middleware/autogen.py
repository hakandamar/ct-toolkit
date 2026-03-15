"""
ct_toolkit.middleware.autogen
------------------------------
Microsoft AutoGen v0.4+ integration for identity continuity.

Provides ``TheseusAutoGenMiddleware`` which hooks into AutoGen's
``ConversableAgent.register_reply()`` mechanism to validate every incoming
message against the Constitutional Kernel and record every outgoing reply in
the Provenance Log.

Optional dependency — requires ``pip install 'ct-toolkit[autogen]'``.
AutoGen does NOT need to be installed for the rest of ct-toolkit to work.

Compatible with pyautogen >= 0.4.

Usage::

    from ct_toolkit import TheseusWrapper
    from ct_toolkit.middleware.autogen import TheseusAutoGenMiddleware
    from autogen import ConversableAgent

    wrapper = TheseusWrapper(provider="openai", kernel_name="defense")

    assistant = ConversableAgent("assistant", llm_config={...})
    TheseusAutoGenMiddleware.apply_to_agent(assistant, wrapper)

    # Now every message sent to/from `assistant` is validated and logged.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from ct_toolkit.core.wrapper import TheseusWrapper
from ct_toolkit.utils.logger import get_logger

logger = get_logger(__name__)

# AutoGen reply function sentinel — return this to indicate "no reply / pass through"
_AUTOGEN_PASS = (False, None)


class TheseusAutoGenMiddleware:
    """
    Middleware for Microsoft AutoGen's ``ConversableAgent``.

    Registers a reply function at position 0 (highest priority) that:
    1. Validates the incoming message against the kernel.
    2. Passes control to the agent's normal reply chain.
    3. Validates the generated reply and records it in the ProvenanceLog.
    4. Warns if ``cascade_blocked`` is True.
    """

    @staticmethod
    def apply_to_agent(
        agent: Any,
        wrapper: TheseusWrapper,
    ) -> None:
        """
        Attach identity-continuity guardrails to an AutoGen ``ConversableAgent``.

        Args:
            agent:   A ``ConversableAgent`` (or any AutoGen agent with
                     ``register_reply``).
            wrapper: The ``TheseusWrapper`` whose kernel rules are enforced.
        """
        if not hasattr(agent, "register_reply"):
            raise TypeError(
                f"agent must be an AutoGen ConversableAgent, got {type(agent).__name__}"
            )

        def _theseus_reply(
            recipient: Any,
            messages: Optional[List[Dict[str, Any]]],
            sender: Optional[Any] = None,
            config: Optional[Any] = None,
        ) -> tuple[bool, Optional[str]]:
            """
            CT Toolkit reply hook for AutoGen.
            Returns (False, None) to let the normal chain produce the reply,
            then post-processes the result for divergence analysis.
            """
            if not messages:
                return _AUTOGEN_PASS

            last_message = messages[-1] if isinstance(messages, list) else messages
            incoming_text = _extract_text(last_message)

            # ── 1. Validate incoming message against kernel ─────────────────
            try:
                wrapper.validate_user_rule(incoming_text)
            except Exception as e:
                logger.warning(f"CT Toolkit | AutoGen kernel violation on incoming message: {e}")
                # Return the error as a response rather than crashing
                return (True, f"[CT Toolkit BLOCKED] {e}")

            # ── 2. Pass through to normal AutoGen reply chain ───────────────
            # Return (False, None) — AutoGen will call the next registered
            # reply function and eventually produce a real response.
            return _AUTOGEN_PASS

        # Register the validation hook at position 1 (just after the
        # termination check at position 0).
        agent.register_reply(
            trigger=lambda sender: True,   # Match all senders
            reply_func=_theseus_reply,
            position=1,
        )

        # Also register a post-reply observer hook for divergence + provenance
        _register_post_reply_hook(agent, wrapper)

        logger.info(
            f"CT Toolkit | AutoGen agent '{getattr(agent, 'name', '?')}' "
            f"wrapped with TheseusAutoGenMiddleware (kernel='{wrapper.kernel.name}')"
        )

    @staticmethod
    def wrap_config_list(
        config_list: List[Dict[str, Any]],
        wrapper: TheseusWrapper,
    ) -> List[Dict[str, Any]]:
        """
        Inject CT Toolkit propagation headers into AutoGen ``config_list``
        entries that support ``api_params``.

        Useful when sub-agents use HTTP-based model endpoints and you want
        the Constitutional Kernel headers propagated at the HTTP level.

        Args:
            config_list: AutoGen model config list.
            wrapper:     The manager's ``TheseusWrapper``.

        Returns:
            A new config list with CT headers injected.
        """
        headers = wrapper.propagate_headers()
        new_config: List[Dict[str, Any]] = []

        for config in config_list:
            cfg = dict(config)
            api_params: Dict[str, Any] = dict(cfg.get("api_params", {}))
            existing_headers: Dict[str, str] = dict(api_params.get("headers", {}))
            existing_headers.update(headers)
            api_params["headers"] = existing_headers
            cfg["api_params"] = api_params
            new_config.append(cfg)

        logger.info(
            f"CT Toolkit | Injected CIK propagation headers into "
            f"{len(new_config)} AutoGen config entries."
        )
        return new_config


# ── Post-reply observer ────────────────────────────────────────────────────────

def _register_post_reply_hook(agent: Any, wrapper: TheseusWrapper) -> None:
    """
    Register a hook that runs AFTER AutoGen generates a reply to analyse
    divergence and record the interaction in the ProvenanceLog.

    AutoGen v0.4 provides ``register_hook("process_message_before_send", fn)``
    for outgoing message interception.
    """
    if not hasattr(agent, "register_hook"):
        # Older AutoGen builds that lack register_hook — log and continue
        logger.debug(
            "CT Toolkit | AutoGen agent does not support register_hook. "
            "Post-reply divergence analysis will be skipped."
        )
        return

    def _post_send_hook(sender: Any, message: Union[Dict[str, Any], str], recipient: Any, silent: bool) -> Union[Dict[str, Any], str]:
        """Analyse and log outgoing messages."""
        content = _extract_text(message)
        if not content:
            return message

        div_result = wrapper._run_divergence_engine(
            message="",
            response=content,
        )

        if div_result.cascade_blocked:
            logger.warning(
                "CT Toolkit | cascade_blocked=True on AutoGen outgoing message. "
                "Consider halting downstream agent calls."
            )

        if wrapper._config.log_requests:
            wrapper._provenance_log.record(
                request_text="[AutoGen Interaction]",
                response_text=content,
                divergence_score=div_result.l1_score,
                metadata={
                    "middleware": "autogen",
                    "tier": div_result.tier.value,
                    "cascade_blocked": div_result.cascade_blocked,
                    "kernel": wrapper.kernel.name,
                },
            )
        return message

    agent.register_hook("process_message_before_send", _post_send_hook)


# ── helpers ────────────────────────────────────────────────────────────────────

def _extract_text(message: Any) -> str:
    """Best-effort text extraction from AutoGen message formats."""
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(message)
