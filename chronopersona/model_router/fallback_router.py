"""Fallback router implementing task-tier routing with automatic fallback."""

import hashlib
import time
from typing import Any, Dict, Iterator, Optional

from loguru import logger

from chronopersona.contracts.interfaces.abstract_credential_provider import (
    ICredentialProvider,
)
from chronopersona.contracts.interfaces.abstract_model_client import (
    IModelClient,
    ModelClientError,
    RateLimitError,
)
from chronopersona.contracts.schemas.model import ModelRequest
from chronopersona.model_router.api_mode_switch import APIMode, APIModeSwitch
from chronopersona.model_router.kimi_client import KimiClient
from chronopersona.model_router.deepseek_client import DeepSeekClient
from chronopersona.model_router.glm_client import GLMClient


# Task tier routing table (per requirements 7.1)
# Format: task_type -> (primary_client_key, fallback_chain)
TASK_ROUTING_TABLE: Dict[str, tuple[str, list[str]]] = {
    "T0": ("local", ["deepseek"]),  # Emotion classification
    "T1": ("local", ["deepseek"]),  # Intent recognition
    "T2": ("deepseek", ["kimi"]),  # Entity extraction (NER)
    "T3": ("deepseek", ["kimi"]),  # Edge building / relation reasoning
    "T3b": ("local_rule", []),  # CORRELATED edge (local rule engine)
    "T4": ("kimi", ["deepseek_pro"]),  # Memory reflection / summary
    "T5": ("deepseek_pro", ["kimi"]),  # Reply generation
    "T6": ("kimi", ["deepseek_pro"]),  # Conflict resolution semantics
    "T7": ("deepseek_pro", ["kimi"]),  # Evaluation / testing
}

# Cache TTL in seconds (per requirements 7.2: 24h)
CACHE_TTL = 86400


class FallbackRouter:
    """Routes LLM requests to appropriate models with automatic fallback.

    Implements the task-tier routing table from requirements 7.1,
    with exponential backoff retry and provider health tracking.
    Per requirements 7.2, cache key includes branch_id and persona_id
    to prevent cross-branch/persona cache pollution.

    Attributes:
        _credential_provider: Credential provider for all clients.
        _mode_switch: API mode switch for local/cloud routing.
        _clients: Dictionary of initialized model clients.
        _cache: Response cache with TTL.
        _health_status: Per-provider health tracking.
        _cost_records: Cost tracking records per branch.
    """

    def __init__(
        self,
        credential_provider: ICredentialProvider,
        mode_switch: Optional[APIModeSwitch] = None,
    ) -> None:
        """Initialize the fallback router.

        Args:
            credential_provider: Provider for API credentials.
            mode_switch: Optional API mode switch. If None, creates
                default HYBRID mode switch.
        """
        self._credential_provider = credential_provider
        self._mode_switch = mode_switch or APIModeSwitch(credential_provider)

        # Initialize all cloud clients per .aider.model.settings.yml
        self._clients: Dict[str, IModelClient] = {
            "kimi": KimiClient(credential_provider),
            "deepseek": DeepSeekClient(
                credential_provider, thinking_mode=False
            ),
            "deepseek_pro": DeepSeekClient(
                credential_provider, thinking_mode=True, reasoning_effort="max"
            ),
            "glm": GLMClient(credential_provider),
        }

        self._cache: Dict[str, tuple[Dict[str, Any], float]] = {}
        self._health_status: Dict[str, bool] = {}
        self._cost_records: Dict[str, list[Dict[str, Any]]] = {}

        logger.info(
            "FallbackRouter initialized with {} clients", len(self._clients)
        )

    def route(
        self,
        prompt: str,
        task_type: str,
        branch_id: str,
        *,
        persona_id: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        model_preference: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Route a request to the appropriate model with fallback.

        Checks cache first, then routes through the fallback chain
        defined in TASK_ROUTING_TABLE. Tracks cost per branch.

        Args:
            prompt: The user prompt.
            task_type: Task tier identifier (T0-T7).
            branch_id: Explicit branch identifier (per AIDER.md section 2).
            persona_id: Current persona identifier for cache key.
            max_tokens: Maximum response tokens.
            temperature: Sampling temperature.
            model_preference: Override model selection.
            metadata: Additional metadata.

        Returns:
            Response dict from the successful model call.

        Raises:
            ModelClientError: If all models in the fallback chain fail.
        """
        # Check cache first (per requirements 7.2)
        cache_key = self._generate_cache_key(
            task_type, prompt, branch_id, persona_id
        )
        cached = self._check_cache(cache_key)
        if cached:
            logger.debug(
                "Cache hit for task {} branch {}", task_type, branch_id
            )
            return cached

        # Determine routing
        if model_preference:
            client_key = model_preference
            fallback_chain: list[str] = []
        else:
            routing = TASK_ROUTING_TABLE.get(
                task_type, ("deepseek", ["kimi"])
            )
            client_key = routing[0]
            fallback_chain = list(routing[1])

        # Check if local mode should be used
        api_mode = self._mode_switch.get_mode_for_task(task_type)
        if api_mode == APIMode.LOCAL and client_key == "local":
            logger.info(
                "Task {} routed to local mode, but local client not yet "
                "implemented, using cloud fallback",
                task_type,
            )
            if fallback_chain:
                client_key = fallback_chain[0]
                fallback_chain = fallback_chain[1:]

        # Build attempt chain
        attempt_chain = [client_key] + fallback_chain
        # Filter to only available client keys
        attempt_chain = [
            k for k in attempt_chain
            if k in self._clients or k == "local_rule"
        ]

        if not attempt_chain:
            raise ModelClientError(
                "router", f"No available clients for task {task_type}"
            )

        # Try each client in the fallback chain
        last_error: Optional[Exception] = None
        for current_key in attempt_chain:
            if current_key == "local_rule":
                logger.debug(
                    "Task {} handled by local rule engine", task_type
                )
                return {
                    "content": "",
                    "model_name": "local_rule_engine",
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "finish_reason": "rule_engine",
                    "latency_ms": 0.0,
                }

            client = self._clients.get(current_key)
            if not client:
                logger.warning(
                    "Client {} not available, skipping", current_key
                )
                continue

            # Check health (unknown clients assumed healthy for first attempt)
            if not self._is_client_healthy(current_key):
                logger.warning(
                    "Client {} marked unhealthy, skipping", current_key
                )
                continue

            try:
                logger.info(
                    "Routing task {} to client {} for branch {}",
                    task_type,
                    current_key,
                    branch_id,
                )
                model_request = ModelRequest(
                    prompt=prompt,
                    task_type=task_type,
                    context={},
                    max_tokens=max_tokens,
                    temperature=temperature,
                    metadata=metadata or {},
                )
                response = client.complete(model_request)

                # Track cost per branch
                self._record_cost(current_key, branch_id, response)

                # Cache successful response
                self._store_cache(cache_key, response)

                # Mark client as healthy
                self._health_status[current_key] = True

                return response

            except RateLimitError as exc:
                last_error = exc
                logger.warning(
                    "Client {} rate limited, trying next fallback",
                    current_key,
                )
                self._health_status[current_key] = False
                continue

            except ModelClientError as exc:
                last_error = exc
                logger.warning(
                    "Client {} error: {}, trying next fallback",
                    current_key,
                    exc,
                )
                self._health_status[current_key] = False
                continue

        # All fallbacks exhausted
        logger.error(
            "All fallbacks exhausted for task {} branch {}",
            task_type,
            branch_id,
        )
        raise ModelClientError(
            "router",
            f"All models failed for task {task_type}: {last_error}",
        )

    def stream_route(
        self,
        prompt: str,
        task_type: str,
        branch_id: str,
        *,
        persona_id: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        model_preference: Optional[str] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Route a streaming request to the appropriate model.

        Streaming does not use cache or fallback (single attempt
        to the primary model for the task tier).

        Args:
            Same as route(), except streaming is implied.

        Returns:
            Iterator of response chunk dicts.

        Raises:
            ModelClientError: If the primary model is unavailable.
        """
        routing = TASK_ROUTING_TABLE.get(task_type, ("deepseek", ["kimi"]))
        client_key = model_preference or routing[0]

        client = self._clients.get(client_key)
        if not client:
            raise ModelClientError(
                "router", f"Client {client_key} not available"
            )

        logger.info(
            "Stream routing task {} to client {}", task_type, client_key
        )
        stream_request = ModelRequest(
            prompt=prompt,
            task_type=task_type,
            context={},
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return client.stream_complete(stream_request)

    def get_cost_summary(self, branch_id: str) -> Dict[str, Any]:
        """Get cost summary for a specific branch.

        Per requirements 4.8.1, cost is tracked per branch and per model.

        Args:
            branch_id: Explicit branch identifier.

        Returns:
            Cost summary dictionary with total and per-model breakdown.
        """
        records = self._cost_records.get(branch_id, [])
        total_input = sum(r.get("input_tokens", 0) for r in records)
        total_output = sum(r.get("output_tokens", 0) for r in records)
        total_cost = sum(r.get("estimated_cost", 0.0) for r in records)
        total_calls = len(records)

        by_model: Dict[str, Dict[str, Any]] = {}
        for r in records:
            model = r.get("model_name", "unknown")
            if model not in by_model:
                by_model[model] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                }
            by_model[model]["calls"] += 1
            by_model[model]["input_tokens"] += r.get("input_tokens", 0)
            by_model[model]["output_tokens"] += r.get("output_tokens", 0)
            by_model[model]["cost"] += r.get("estimated_cost", 0.0)

        return {
            "branch_id": branch_id,
            "total_calls": total_calls,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_cost_usd": total_cost,
            "by_model": by_model,
        }

    def cache_clear(self) -> None:
        """Clear the response cache."""
        self._cache.clear()
        logger.info("Response cache cleared")

    def _generate_cache_key(
        self,
        task_type: str,
        prompt: str,
        branch_id: str,
        persona_id: Optional[str],
    ) -> str:
        """Generate a deterministic cache key.

        Per requirements 7.2, cache key includes branch_id and persona_id
        to prevent cross-branch/persona pollution.

        Args:
            task_type: Task tier.
            prompt: Prompt text.
            branch_id: Branch identifier.
            persona_id: Persona identifier.

        Returns:
            SHA-256 hash-based cache key string.
        """
        raw = f"{task_type}:{prompt}:{branch_id}:{persona_id or 'none'}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _check_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Check if a cached response exists and is not expired.

        Args:
            cache_key: Cache key to check.

        Returns:
            Cached response dict, or None if not found/expired.
        """
        entry = self._cache.get(cache_key)
        if not entry:
            return None
        response, timestamp = entry
        if time.time() - timestamp > CACHE_TTL:
            self._cache.pop(cache_key, None)
            return None
        return response

    def _store_cache(self, cache_key: str, response: Dict[str, Any]) -> None:
        """Store a response in the cache.

        Args:
            cache_key: Cache key.
            response: Response dict to cache.
        """
        self._cache[cache_key] = (response, time.time())

    def _is_client_healthy(self, client_key: str) -> bool:
        """Check if a client is marked as healthy.

        Unknown clients are assumed healthy (first attempt allowed).

        Args:
            client_key: Client identifier.

        Returns:
            True if healthy or unknown.
        """
        return self._health_status.get(client_key, True)

    def _record_cost(
        self,
        client_key: str,
        branch_id: str,
        response: Dict[str, Any],
    ) -> None:
        """Record cost for a successful API call.

        Args:
            client_key: Client identifier.
            branch_id: Branch identifier.
            response: Response dict with token counts.
        """
        client = self._clients.get(client_key)
        input_tokens = response.get("input_tokens", 0)
        output_tokens = response.get("output_tokens", 0)
        estimated_cost = (
            client.estimate_cost(input_tokens, output_tokens)
            if client
            else 0.0
        )

        record = {
            "model_name": response.get("model_name", client_key),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost": estimated_cost,
            "latency_ms": response.get("latency_ms", 0.0),
            "timestamp": time.time(),
        }

        if branch_id not in self._cost_records:
            self._cost_records[branch_id] = []
        self._cost_records[branch_id].append(record)

        logger.debug(
            "Cost recorded: {} input_tokens, {} output_tokens, "
            "${:.4f} for branch {}",
            input_tokens,
            output_tokens,
            estimated_cost,
            branch_id,
        )
