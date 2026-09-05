"""Versioned prompt registry.

A prompt is content, not code that happens to be a string. Each one carries a
version, and its sha256 is written to ai_runs on every call. Editing a template
without bumping the version breaks the audit trail, so the loader refuses to
let two versions share a name.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    name: str
    version: str
    purpose: str
    schema_name: str
    template: str
    # Returned when AI_ENABLED=false, so every code path is exercised offline.
    fixture: Callable[[dict[str, Any]], dict[str, Any]] = field(
        default=lambda _: {"fixture": True}
    )

    def render(self, variables: dict[str, Any]) -> str:
        return self.template.format(**variables)


_REGISTRY: dict[str, PromptTemplate] = {}


def register(prompt: PromptTemplate) -> PromptTemplate:
    key = prompt.name
    if key in _REGISTRY and _REGISTRY[key].version != prompt.version:
        raise ValueError(f"prompt {key} registered twice with different versions")
    _REGISTRY[key] = prompt
    return prompt


def get(name: str) -> PromptTemplate:
    return _REGISTRY[name]


def all_prompts() -> dict[str, PromptTemplate]:
    return dict(_REGISTRY)


# --- Phase 0 placeholders -------------------------------------------------
# Real templates arrive with their phases. These exist so the registry, the
# ai_runs plumbing and the fixture path are exercised from day one.

CONCEPT_EXTRACTION = register(
    PromptTemplate(
        name="concept_extraction",
        version="0.1.0",
        purpose="concept_extraction",
        schema_name="ConceptSet",
        template="Extract concepts from the material below.\n\n{material}",
        fixture=lambda v: {"concepts": [], "insufficient_evidence": True},
    )
)

QUESTION_GENERATION = register(
    PromptTemplate(
        name="question_generation",
        version="0.1.0",
        purpose="question_generation",
        schema_name="QuestionDraft",
        template="Write one question testing {concept}, grounded only in:\n\n{evidence}",
        fixture=lambda v: {"questions": [], "insufficient_evidence": True},
    )
)

RESPONSE_ANALYSIS = register(
    PromptTemplate(
        name="response_analysis",
        version="0.1.0",
        purpose="response_analysis",
        schema_name="AttemptDiagnosis",
        template="Analyse this response:\n\n{response}\n\nQuestion:\n{question}",
        fixture=lambda v: {
            "diagnosis": "insufficient_evidence",
            "confidence": 0.0,
            "observations": [],
            "alternatives": [],
        },
    )
)
