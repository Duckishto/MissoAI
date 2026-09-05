# Architecture, Phase 0

## Topology

```
browser
  │  https://app.example.com
  ▼
adaptive-web (Worker)                Next.js 16 via @opennextjs/cloudflare
  ├── ASSETS                         static output
  └── NEXT_INC_CACHE_KV              ISR cache
  │
  │  https://api.example.com
  ▼
adaptive-api (Worker)                thin router, holds the secrets
  ├── /edge-health                   answered at the edge, never wakes the container
  ├── MEDIA (R2)                     learner images, handwriting, diagrams
  └── BACKEND (Durable Object → Container)
        │
        ▼
      FastAPI, uvicorn, port 8000
        │
        ▼
      Neon Postgres 16 + pgvector    direct TCP from the container
```

The container reaches Postgres over plain TCP, so Hyperdrive is not in the
path. Add it only if the Worker itself starts querying.

## Why this shape

Cloudflare's native runtime is V8 isolates, which do not run FastAPI.
Containers and Sandboxes went GA in April 2026 on the Workers Paid plan, which
makes a Python backend on Cloudflare viable. The Worker in front exists because
three things belong at the edge and nowhere else: secrets, the R2 binding, and
a health check that does not cost a cold start.

## Things this choice costs you

**Regional footprint.** Containers deploy to fewer locations than the Workers
edge, and Southeast Asia is thinner than Europe or North America. Worker to
container latency is low once an instance is warm nearby; the first request to
an uncached region is not. Measure from your actual pilot location before the
study, not from a laptop on a fast connection.

**Cold starts.** `sleepAfter` is set to 15 minutes and a single named instance
(`"main"`) is used, so the pool stays warm across a session and participants
share it. If a study session has long gaps, either raise `sleepAfter` or accept
the wake latency and record it — a cold start that lands inside a timed item is
a confound, not a nuisance.

**Log retention.** Container logs live in the dashboard for about a week. That
is fine for debugging and useless for a study. Anything you need at analysis
time goes into Postgres: `interactions`, `ai_runs`, `selection_decisions`. Ship
stdout to Axiom or Better Stack for the rest.

**Coupling.** The Worker plus Durable Object plus Container arrangement is
Cloudflare-specific. The FastAPI app itself is not — it is a plain uvicorn
process reading `DATABASE_URL` from the environment, so moving it to Fly.io or
Render is a Dockerfile and a DNS record. Keep it that way: no Cloudflare-only
APIs inside `app/`.

## Request identity

The browser sees `x-request-id` on every response. Inside, the same value comes
from `CF-Ray` when Cloudflare supplies one, is bound to every structlog line by
`RequestContextMiddleware`, and is written to `ai_runs.request_id` and
`interactions.request_id`. One id joins a browser network entry, a Worker log,
a container log, a model call and an event row.

## Data model, the parts that matter

Ordinary tables: users, courses, concepts, questions, attempts, sessions.

Append-only, enforced by trigger: `interactions`, `learner_state_history`,
`ai_runs`, `selection_decisions`. `UPDATE` and `DELETE` raise.

`learner_states` holds the current estimate and is mutable;
`learner_state_history` records every transition with the model version that
produced it. Together they answer "what did the system believe at 14:32 on the
third item", which is the question a reviewer asks.

Instrument isolation is three triggers, not a code convention:

1. `instrument_items_fixed_only` — a question joining an instrument must carry
   `is_fixed_instrument`, which is what keeps it out of `adaptive_question_pool`.
2. `instrument_items_locked` — a locked instrument cannot gain or lose items.
3. `questions_locked_immutable` — a question inside a locked instrument cannot
   have its stem, options or correct answer edited.

`study_participants.condition` is frozen at enrolment by a fourth trigger.

## The AI seam

Nothing calls a provider directly. `app/modules/ai/client.run()` is the only
door, and it always writes an `ai_runs` row, success or failure. Prompts are
registered objects with a name, a version and a fixture, and their sha256 is
recorded per call. Editing a template without bumping the version breaks the
audit trail, so the registry refuses two versions under one name.

With `AI_ENABLED=false` the fixture path runs and still writes the row. The
calling code is identical in both modes, which is why Phase 0 can be built,
tested and demoed without a token budget, and why turning the model on in
Phase 1 changes one environment variable rather than a call graph.

## Where the phases land

| Phase | Module | Currently |
|---|---|---|
| 1 | `content` | ingest, chunk, embed |
| 1 | `concepts` | extraction, dedup, prerequisite edges |
| 2 | `assessment` | generation, validation, repair |
| 2 | `assessment` | grading and response analysis |
| 3 | `learner` | `compute_update` returns state unchanged |
| 3 | `adaptive` | `selector` picks the next unseen item in order |
| 4 | `research` | consent, randomisation, exports |
