"""Single choke point for every model call.

Two rules hold here and nowhere else:
  1. No module talks to a provider directly. Everything goes through `run`.
  2. Every call writes exactly one ai_runs row, success or failure, and the
     caller gets the run id back so the artefact can reference it.

With AI_ENABLED=false the fixture path runs instead. It still writes an
ai_runs row, so the audit trail and the calling code are identical in both
modes and Phase 0 can be built and tested without spending tokens.
"""

import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.audit import AiRun
from app.modules.ai.prompts import PromptTemplate

log = get_logger("ai")


@dataclass(slots=True)
class AiResult:
    run_id: UUID
    data: dict[str, Any]
    ok: bool
    error: str | None = None


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


async def run(
    db: AsyncSession,
    *,
    prompt: PromptTemplate,
    variables: dict[str, Any],
    request_id: str | None = None,
    temperature: float = 0.0,
    seed: int | None = 1,
) -> AiResult:
    settings = get_settings()
    rendered = prompt.render(variables)
    params = {
        "temperature": temperature,
        "seed": seed,
        "max_output_tokens": settings.ai_max_output_tokens,
        "response_format": "json_schema",
        "schema_name": prompt.schema_name,
    }

    started = time.perf_counter()
    ok, error, output = True, None, None
    try:
        if settings.ai_enabled:
            output = await _call_provider(rendered, params)
        else:
            output = prompt.fixture(variables)
    except Exception as exc:  # noqa: BLE001 - recorded, then surfaced
        ok, error = False, f"{type(exc).__name__}: {exc}"
        log.warning("ai_call_failed", purpose=prompt.purpose, error=error)

    latency_ms = int((time.perf_counter() - started) * 1000)

    record = AiRun(
        purpose=prompt.purpose,
        provider="cloudflare-ai-gateway" if settings.ai_enabled else "fixture",
        model=settings.ai_model if settings.ai_enabled else "fixture",
        prompt_name=prompt.name,
        prompt_version=prompt.version,
        prompt_sha256=_sha256(prompt.template),
        input_sha256=_sha256(_canonical(variables)),
        params=params,
        raw_output=output,
        ok=ok,
        error=error,
        latency_ms=latency_ms,
        request_id=request_id,
    )
    db.add(record)
    await db.flush()

    return AiResult(run_id=record.id, data=output or {}, ok=ok, error=error)


def _auth_headers(settings: Any) -> dict[str, str]:
    headers = {
        "anthropic-version": settings.ai_anthropic_version,
        "content-type": "application/json",
    }
    key = settings.ai_api_key or ""
    if settings.ai_auth_scheme == "bearer":
        headers["authorization"] = f"Bearer {key}"
    else:
        headers["x-api-key"] = key
    return headers


def _extract_text(payload: dict[str, Any]) -> str:
    """Join the text blocks of a Messages API response."""
    blocks = payload.get("content") or []
    return "\n".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()


def _parse_json_body(text: str) -> dict[str, Any]:
    """Models wrap JSON in fences often enough that stripping them is routine.

    A parse failure raises, which the caller records on the ai_runs row rather
    than silently substituting an empty result.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return json.loads(cleaned)


async def _call_provider(rendered: str, params: dict[str, Any]) -> dict[str, Any]:
    """Call the Messages API and return parsed JSON.

    The endpoint has no schema-enforced output mode, so the system prompt
    demands bare JSON and the response is parsed here. Anything unparseable is
    an error, not something to paper over.
    """
    settings = get_settings()
    if not settings.ai_api_key:
        raise RuntimeError("AI_ENABLED is true but AI_API_KEY is not set")

    body: dict[str, Any] = {
        "model": settings.ai_model,
        "max_tokens": params["max_output_tokens"],
        "temperature": params["temperature"],
        "system": (
            "Respond with a single JSON object matching the requested schema. "
            "No prose, no explanation, no markdown fences."
        ),
        "messages": [{"role": "user", "content": rendered}],
    }

    url = settings.ai_base_url.rstrip("/") + "/v1/messages"
    async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as http:
        response = await http.post(url, headers=_auth_headers(settings), json=body)

    if response.status_code >= 400:
        raise RuntimeError(f"provider returned {response.status_code}: {response.text[:300]}")

    payload = response.json()
    parsed = _parse_json_body(_extract_text(payload))
    usage = payload.get("usage") or {}
    parsed["_usage"] = {
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
    }
    return parsed


async def check_provider() -> dict[str, Any]:
    """Confirm the key reaches the provider, via /v1/me.

    The upstream response carries account email and credit balance. Those are
    logged, never returned, so a public health endpoint cannot disclose them.
    """
    settings = get_settings()
    url = settings.ai_base_url.rstrip("/") + "/v1/me"
    try:
        async with httpx.AsyncClient(timeout=30.0) as http:
            response = await http.get(url, headers=_auth_headers(settings))
    except Exception as exc:  # noqa: BLE001 - reported as unreachable
        log.warning("provider_unreachable", error=str(exc))
        return {"status": 0}
    if response.status_code != 200:
        log.warning("provider_check_failed", status=response.status_code)
    return {"status": response.status_code}
