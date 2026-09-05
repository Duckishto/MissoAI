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
import time
from dataclasses import dataclass
from typing import Any
from uuid import UUID

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


async def _call_provider(rendered: str, params: dict[str, Any]) -> dict[str, Any]:
    """Phase 1. Route through AI Gateway so spend and caching are enforced
    outside the application.
    """
    raise NotImplementedError(
        "Provider calls land in Phase 1. Run with AI_ENABLED=false until then."
    )
