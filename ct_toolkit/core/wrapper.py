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
  5. Staged Approval (Cooldown): Risky kernel updates are monitored via shadow requests
     before being promoted to production.
"""
from __future__ import annotations

import time
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Callable, Dict, List

import litellm

from ct_toolkit.core.kernel import ConstitutionalKernel
from ct_toolkit.core.compatibility import CompatibilityLayer, CompatibilityResult
from ct_toolkit.core.exceptions import (
    MissingClientError, 
    CriticalSandboxDivergenceError
)
from ct_toolkit.core.integrity import IntegrityMonitor
from ct_toolkit.divergence.scheduler import RiskProfile
from ct_toolkit.core.compression_guard import ContextCompressionGuard
from ct_toolkit.endorsement.reflective import (
    ReflectiveEndorsement, 
    StagedUpdateManager,
    CooldownCalculator
)
from ct_toolkit.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WrapperConfig:
    """TheseusWrapper configuration."""
    project_root: str | Path | None = None
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
    drift_alert_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    judge_client: Any = None         # Separate provider client for L2/L3
    embedding_client: Any = None     # Client for L1 ECS embedding (falls back to main client if compatible)
    embedding_model: str = "text-embedding-3-small"
    enterprise_mode: bool = False    # Run all tiers all the time
    parent_kernel: ConstitutionalKernel | None = None  # Propagated from mother agent
    
    # -- Auto-Correction Loop --
    auto_correction: bool = False
    max_correction_retries: int = 1

    # -- Dynamic Stability-Plasticity Scheduling --
    elasticity_max_thresholds: tuple[float, float, float] | None = None  # (max_l1, max_l2, max_l3)
    elasticity_growth_rate: float | None = None
    risk_profile: RiskProfile | None = None

    strict_embedding: bool = False   # Raise error if embedding API fails

    # -- Context Compression Guard --
    compression_threshold: float = 0.85
    compression_passive_detection: bool = True

    # -- Staged Approval (Cooldown) --
    endorsement_cooldown_base: int = CooldownCalculator.DEFAULT_BASE_SECONDS
    endorsement_cooldown_max: int = CooldownCalculator.DEFAULT_MAX_SECONDS
    endorsement_no_probe_penalty: int = CooldownCalculator.DEFAULT_NO_PROBE_PENALTY_S


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
    # Sandbox metadata if staged updates are active
    sandbox_divergence: float | None = None

    def __str__(self) -> str:
        return self.content


class TheseusWrapper:
    """
    Identity-continuity proxy wrapping the LLM API client.

    Supported providers: openai (default), anthropic, ollama, google, etc.
    (Any provider supported by LiteLLM)

    Usage:
        from ct_toolkit import TheseusWrapper
        
        # 1. Using a specific provider (Simplest)
        client = TheseusWrapper(provider="openai")
        
        # 2. Wrapping an existing client (Backward compatible)
        import openai
        client = TheseusWrapper(openai.OpenAI())

        response = client.chat("Hello, how can I help you?", model="gpt-4o-mini")
        print(response.content)
        print(f"Divergence: {response.divergence_score}")
    """

    def __init__(
        self,
        client: Any = None,
        config: WrapperConfig | None = None,
        *,
        provider: str | None = None,
        kernel_path: str | Path | None = None,
        template: str = "general",
        kernel_name: str = "default",
        project_root: str | Path | None = None,
    ) -> None:
        """
        Initializes TheseusWrapper.
        """
        self._config = config or WrapperConfig(
            kernel_path=kernel_path,
            template=template,
            kernel_name=kernel_name,
            project_root=project_root,
        )
        
        if client is None and provider is None:
            # Default to openai if nothing specified
            provider = "openai"
            
        self._client = client
        self._provider = provider or self._detect_provider(client)
        self._project_root = (
            Path(self._config.project_root)
            if self._config.project_root
            else Path(os.getcwd())
        )
        self._kernel = self._load_kernel()

        # If a parent kernel exists, merge it into our own kernel as axiomatic constraints
        if self._config.parent_kernel:
            logger.info(f"Merging parent kernel '{self._config.parent_kernel.name}' into current kernel.")
            self._kernel = self._kernel.merge(self._config.parent_kernel)
        self._compatibility: CompatibilityResult = CompatibilityLayer.check(
            template=self._config.template,
            kernel=self._config.kernel_name,
        )
        self._provenance_log = self._init_provenance_log()
        self._identity_layer = self._init_identity_layer()
        self._divergence_engine = self._init_divergence_engine()
        self._last_model: str = "unknown"

        # ── Context Compression Guard ──
        self._compression_guard = ContextCompressionGuard(
            self, 
            threshold=self._config.compression_threshold
        )
        self._shadow_history: Optional[List[Dict[str, str]]] = None

        # ── Staged Approval (Cooldown) ──
        self._staged_manager = StagedUpdateManager()

        # ── Integrity Monitoring ──
        self._integrity_monitor = IntegrityMonitor()
        self._register_monitored_files()

        self._log_init()

    def _register_monitored_files(self):
        """
        Finds and registers all critical configuration files for integrity monitoring.
        """
        logger.debug("Registering configuration files for integrity monitoring.")
        
        # 1. Scan built-in package files
        try:
            from importlib.resources import files
            package_root = files("ct_toolkit")
            
            internal_patterns = [
                "kernels/**/*.yaml",
                "identity/templates/**/*.yaml",
                "endorsement/probes/**/*.json",
            ]

            for pattern in internal_patterns:
                for file_path in package_root.rglob(pattern):
                    if file_path.is_file():
                        self._integrity_monitor.register_file(file_path)

        except Exception:
            package_root = Path(__file__).parent.parent
            for pattern in internal_patterns:
                for file_path in package_root.rglob(pattern):
                    if file_path.is_file():
                        self._integrity_monitor.register_file(file_path)

        # 2. Scan user's custom config directory
        if self._project_root:
            user_config_dir = self._project_root / "config"
            if user_config_dir.is_dir():
                logger.debug(f"Scanning user config directory for integrity monitoring: {user_config_dir}")
                user_patterns = ["*_kernel.yaml", "*_identity.yaml", "*_probes.json", "*.yaml", "*.json"]
                for pattern in user_patterns:
                    for file_path in user_config_dir.rglob(pattern):
                        if file_path.is_file():
                            self._integrity_monitor.register_file(file_path)


    # ── Factory / Init ─────────────────────────────────────────────────────────

    def _detect_provider(self, client: Any) -> str:
        if client is None:
            return "unknown"
            
        if isinstance(client, str):
            return client.lower()

        try:
            if hasattr(client, "provider") and isinstance(client.provider, str):
                return client.provider

            module = type(client).__module__.lower()
            if "openai" in module: return "openai"
            if "anthropic" in module: return "anthropic"
            if "ollama" in module: return "ollama"
            if "google" in module: return "google"
            if "cohere" in module: return "cohere"
            if "mistral" in module: return "mistral"
        except:
            pass
        return "unknown"

    def _load_kernel(self) -> ConstitutionalKernel:
        if self._config.kernel_path:
            logger.debug(f"Loading kernel from explicit path: {self._config.kernel_path}")
            return ConstitutionalKernel.from_yaml(self._config.kernel_path)

        safe_name = os.path.basename(self._config.kernel_name)
        
        if self._project_root:
            user_config_path = self._project_root / "config" / f"{safe_name}.yaml"
            if user_config_path.exists():
                logger.debug(f"Loading kernel from user config: {user_config_path}")
                return ConstitutionalKernel.from_yaml(user_config_path)

        try:
            from importlib.resources import files
            kernel_resource = files("ct_toolkit.kernels").joinpath(f"{safe_name}.yaml")
            if kernel_resource.is_file():
                logger.debug(f"Loading built-in kernel: {safe_name}.yaml")
                return ConstitutionalKernel.from_yaml(kernel_resource)
        except (ImportError, FileNotFoundError):
            kernel_path = (
                Path(__file__).parent.parent
                / "kernels"
                / f"{safe_name}.yaml"
            )
            if kernel_path.exists():
                logger.debug(f"Loading built-in kernel (fallback): {kernel_path}")
                return ConstitutionalKernel.from_yaml(kernel_path)

        logger.warning(
            f"Kernel '{self._config.kernel_name}' not found in user config or built-ins. Using default."
        )
        return ConstitutionalKernel.default()

    def _init_provenance_log(self) -> Any:
        from ct_toolkit.provenance.log import ProvenanceLog
        return ProvenanceLog(
            vault_type=self._config.vault_type,
            vault_path=self._config.vault_path,
        )

    def _init_identity_layer(self) -> Any:
        from ct_toolkit.identity.embedding import IdentityEmbeddingLayer
        
        emb_client = self._config.embedding_client
        if emb_client is None:
            if self._provider == "openai":
                emb_client = self._client
            else:
                logger.debug(f"Provider {self._provider} does not support default embeddings. Falling back to local.")

        return IdentityEmbeddingLayer(
            template=self._config.template,
            embedding_client=emb_client,
            embedding_model=self._config.embedding_model,
            project_root=self._project_root,
            strict_embedding=self._config.strict_embedding,
        )

    def _init_divergence_engine(self) -> Any:
        from ct_toolkit.divergence.engine import DivergenceEngine
        from ct_toolkit.divergence.scheduler import ElasticityScheduler
        
        scheduler = None
        if self._config.elasticity_max_thresholds and self._config.elasticity_growth_rate:
            scheduler = ElasticityScheduler(
                base_thresholds=(
                    self._config.divergence_l1_threshold,
                    self._config.divergence_l2_threshold,
                    self._config.divergence_l3_threshold
                ),
                max_thresholds=self._config.elasticity_max_thresholds,
                growth_rate=self._config.elasticity_growth_rate,
                risk_profile=self._config.risk_profile
            )

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
            scheduler=scheduler,
            project_root=self._project_root,
            provenance_log=self._provenance_log,
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
        """
        # --- Pre-flight Checks ---
        self._integrity_monitor.verify_integrity()
        self._process_staged_updates()

        composed_system = self._compose_system_prompt(system)
        messages = self._build_messages(message, history, composed_system)

        if self._client is None and not self._has_env_credentials():
            raise MissingClientError(
                f"No client provided and no environment credentials found for provider '{self._provider}'. "
                f"Please provide a client or set the appropriate environment variables."
            )

        retries = 0
        max_retries = self._config.max_correction_retries if self._config.auto_correction else 0
        
        while retries <= max_retries:
            start_time = time.monotonic()
    
            try:
                raw_response = self._call_provider(messages, model=model, **kwargs)
            except Exception as e:
                logger.error(f"Provider API error: {e}")
                raise
    
            elapsed = time.monotonic() - start_time
            content = self._extract_content(raw_response)
            model_used = self._extract_model(raw_response, model)
            self._last_model = model_used
    
            # Compute current interaction experience
            interaction_count = 0
            if self._config.log_requests:
                interaction_count = self._provenance_log.get_interaction_count(
                    template=self._config.template,
                    kernel_name=self._kernel.name,
                    model=model_used
                )
    
            # Divergence Engine (L1 -> L2 -> L3)
            skip_l3 = self._config.auto_correction and retries < max_retries
            div_result = self._run_divergence_engine(
                message=message,
                response=content,
                interaction_count=interaction_count,
                skip_l3=skip_l3,
            )
            
            from ct_toolkit.divergence.l2_judge import JudgeVerdict
            if getattr(div_result, 'l2_verdict', None) == JudgeVerdict.MISALIGNED and retries < max_retries:
                logger.warning(f"Auto-correction triggered. Reason: {div_result.l2_reason}")
                messages.extend([
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": f"Identity Drift Detected. Your previous response violated the core identity instructions. Reason: {div_result.l2_reason}. Please revise your response to strictly adhere to the system prompt."}
                ])
                retries += 1
                continue
                
            break

        # --- Staged Approval Monitoring (Shadow Requests) ---
        sandbox_divergence = None
        if self._staged_manager.has_active_staged():
            sandbox_divergence = self._run_shadow_requests(message, history, model, **kwargs)

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
                    "drift_alert_enabled": self._config.drift_alert_callback is not None,
                    "sandbox_divergence": sandbox_divergence,
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
            sandbox_divergence=sandbox_divergence,
        )

    # ── Shadow Request Logic ──────────────────────────────────────────────────

    def _run_shadow_requests(
        self,
        message: str,
        history: list[dict[str, str]] | None,
        model: str | None,
        **kwargs: Any,
    ) -> float | None:
        """
        Runs the interaction against one or more 'staged' (sandbox) kernels
        to observe if the proposed changes cause identity drift.
        """
        active_staged = self._staged_manager.get_active()
        if not active_staged:
            return None

        # To keep it simple, we monitor the first active staged update
        staged_record = active_staged[0]
        
        # 1. Clone current kernel and apply the staged rule
        sandbox_kernel = ConstitutionalKernel.from_dict(self._kernel.to_dict())
        try:
            sandbox_kernel.update_commitment(
                staged_record.commitment_id, 
                staged_record.rule_text
            )
        except Exception as e:
            logger.error(f"Failed to apply staged rule to sandbox kernel: {e}")
            return None

        # 2. Call provider with sandbox kernel
        sandbox_system = sandbox_kernel.get_system_prompt_injection()
        sandbox_messages = self._build_messages(message, history, sandbox_system)
        
        try:
            # We use the same model/client as the live request
            sandbox_response = self._call_provider(sandbox_messages, model=model, **kwargs)
            sandbox_content = self._extract_content(sandbox_response)
            
            # 3. Analyze sandbox divergence
            sandbox_div_score = self._identity_layer.compute_divergence(sandbox_content)
            
            # 4. Critical Divergence Check
            if sandbox_div_score >= self._config.divergence_l3_threshold:
                reason = f"Sandbox divergence L1 score {sandbox_div_score:.4f} exceeded L3 threshold."
                self._staged_manager.reject_staged(staged_record.id, reason=reason)
                raise CriticalSandboxDivergenceError(
                    endorsement_id=staged_record.id,
                    l1_score=sandbox_div_score,
                    reason=reason
                )
            
            return sandbox_div_score

        except CriticalSandboxDivergenceError:
            raise
        except Exception as e:
            logger.warning(f"Shadow request for staged update failed: {e}")
            return None

    def _process_staged_updates(self) -> None:
        """
        Checks for staged updates whose cooldown has expired and
        promotes them to the production kernel.
        """
        promotable = self._staged_manager.get_promotable()
        for record in promotable:
            try:
                logger.info(
                    f"Promoting staged endorsement to production: {record.id[:8]}... "
                    f"rule='{record.rule_text}'"
                )
                self._kernel.update_commitment(record.commitment_id, record.rule_text)
                
                # Write promotion event to log
                if self._config.log_requests:
                    self._provenance_log.record(
                        request_text=f"[COOLDOWN_EXPIRED] Promoting staged rule",
                        response_text=f"Rule applied to production kernel: {record.rule_text}",
                        metadata={
                            "event_type": "staged_promotion",
                            "endorsement_id": record.id,
                            "kernel": self._kernel.name,
                            "commitment_id": record.commitment_id,
                        }
                    )
            except Exception as e:
                logger.error(f"Failed to promote staged update {record.id[:8]}: {e}")

    # ── Provider Dispatch ──────────────────────────────────────────────────────

    def _has_env_credentials(self) -> bool:
        """Checks if environment variables for the current provider are set."""
        import os
        if self._provider == "openai":
            return bool(os.environ.get("OPENAI_API_KEY"))
        if self._provider == "anthropic":
            return bool(os.environ.get("ANTHROPIC_API_KEY"))
        if self._provider == "ollama":
            return True
        if self._provider == "google":
            return bool(os.environ.get("GOOGLE_API_KEY"))
        return False

    def _call_provider(
        self,
        messages: list[dict[str, str]],
        model: str | None,
        **kwargs: Any,
    ) -> Any:
        """Uses LiteLLM for unified provider calling."""
        if self._config.compression_passive_detection and self._shadow_history:
            if len(messages) < len(self._shadow_history) * 0.7:
                self._compression_guard.on_passive_detection(
                    original=self._shadow_history,
                    compressed=messages
                )

        self._shadow_history = list(messages)
        
        if not model:
            if self._provider == "openai": model = "gpt-4o-mini"
            elif self._provider == "anthropic": model = "claude-3-5-sonnet-latest"
            elif self._provider == "ollama": model = "llama3"
            else: model = "gpt-4o-mini"

        full_model = model
        if ":" in model and self._provider != "ollama":
             full_model = model.replace(":", "/", 1)
        elif self._provider not in ("openai", "unknown") and not (":" in model and self._provider == "ollama"):
             if not model.startswith(f"{self._provider}/"):
                  full_model = f"{self._provider}/{model}"

        # Ensure ollama always has prefix if it has a colon
        if self._provider == "ollama" and ":" in model and not full_model.startswith("ollama/"):
             full_model = f"ollama/{full_model}"

        if hasattr(self._client, "base_url") and self._client.base_url:
            kwargs["api_base"] = str(self._client.base_url)
        if hasattr(self._client, "api_key") and self._client.api_key:
            kwargs["api_key"] = self._client.api_key

        if hasattr(self._client, "timeout") and "timeout" not in kwargs:
            kwargs["timeout"] = self._client.timeout

        try:
            return litellm.completion(model=full_model, messages=messages, **kwargs)
        except Exception as e:
            logger.error(f"litellm call failed: {e}")
            raise

    # ── Helper Methods ──────────────────────────────────────────────────────

    def _compose_system_prompt(self, extra: str | None) -> str:
        kernel_injection = self._kernel.get_system_prompt_injection()
        
        if any(a.id.startswith("propagated_") for a in self._kernel.anchors):
            kernel_injection = (
                "# Mother Agent Constraints\n"
                "You are operating under constraints propagated from a Mother Agent. "
                "These rules take absolute precedence over any other instructions.\n\n"
                f"{kernel_injection}"
            )

        if extra:
            return f"{kernel_injection}\n{extra}"
        return kernel_injection

    def propagate_headers(self) -> dict[str, str]:
        """
        Returns a dictionary of headers to be used when calling sub-agents.
        """
        import json
        import base64
        
        kernel_data = self._kernel.to_dict()
        kernel_data["is_readonly"] = True
        
        encoded_kernel = base64.b64encode(json.dumps(kernel_data).encode()).decode()
        
        return {
            "X-CT-Kernel": encoded_kernel,
            "X-CT-Parent-Provider": self._provider,
            "X-CT-Parent-Model": getattr(self, "_last_model", "unknown")
        }

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
        if isinstance(raw, dict):
            if "choices" in raw and isinstance(raw["choices"], list) and raw["choices"]:
                return raw["choices"][0].get("message", {}).get("content", "") or ""
            if "message" in raw:
                return raw["message"].get("content", "") or ""
            return str(raw)

        try:
            if hasattr(raw, "choices") and raw.choices:
                choice = raw.choices[0]
                if hasattr(choice, "message") and choice.message:
                    return choice.message.content or ""
                if hasattr(choice, "text"):
                    return choice.text or ""
        except Exception:
            pass
            
        if hasattr(raw, "content") and isinstance(raw.content, list):
             return raw.content[0].text if raw.content else ""
        if hasattr(raw, "message"):
             return getattr(raw.message, "content", "") or ""
             
        return str(raw)

    def _extract_model(self, raw: Any, fallback: str | None) -> str:
        if isinstance(raw, dict) and "model" in raw:
            return raw["model"]
        if hasattr(raw, "model"):
            return raw.model
        return fallback or "unknown"

    def _run_divergence_engine(self, message: str, response: str, interaction_count: int = 0, skip_l3: bool = False) -> Any:
        try:
            return self._divergence_engine.analyze(message, response, interaction_count, skip_l3=skip_l3)
        except Exception as e:
            logger.error(f"Divergence Engine execution failed: {e}")
            from ct_toolkit.divergence.engine import DivergenceResult, DivergenceTier
            return DivergenceResult(
                tier=DivergenceTier.OK,
                summary=f"Engine execution failed: {e}"
            )

    # ── Kernel Management ────────────────────────────────────────────────────────

    def validate_user_rule(self, rule_text: str) -> None:
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
        flow if there is a plastic conflict.
        """
        from ct_toolkit.endorsement.reflective import ReflectiveEndorsement

        re = ReflectiveEndorsement(
            kernel=self._kernel,
            provenance_log=self._provenance_log,
            approval_channel=approval_channel,
            staged_manager=self._staged_manager,
            cooldown_base_s=self._config.endorsement_cooldown_base,
            cooldown_max_s=self._config.endorsement_cooldown_max,
            no_probe_penalty_s=self._config.endorsement_no_probe_penalty,
            template=self._config.template,
        )
        return re.validate_and_endorse(
            rule_text=rule_text,
            operator_id=operator_id,
            commitment_new_value=commitment_new_value,
        )

    def export_provenance_log(self) -> list[dict[str, Any]]:
        return self._provenance_log.export_log()

    @property
    def kernel(self) -> ConstitutionalKernel:
        return self._kernel

    @property
    def compatibility(self) -> CompatibilityResult:
        return self._compatibility

    @property
    def divergence_engine(self) -> Any:
        return self._divergence_engine

    @property
    def staged_manager(self) -> StagedUpdateManager:
        return self._staged_manager

    def __repr__(self) -> str:
        return (
            f"TheseusWrapper("
            f"provider={self._provider!r}, "
            f"kernel={self._kernel.name!r}, "
            f"template={self._config.template!r})"
        )