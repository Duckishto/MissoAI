# Adaptive assessment — Phase 0

Engineering foundation for a multimodal adaptive assessment system. This phase
contains no intelligence. It contains the places intelligence will go, and the
guarantees that have to be true before any of it is trustworthy.

## What runs

```
Cloudflare
├── adaptive-web       Worker · Next.js 16 via @opennextjs/cloudflare
│   └── KV             ISR / page cache
└── adaptive-api       Worker · thin router
    ├── Container      FastAPI, Python 3.12, port 8000
    └── R2 (MEDIA)     learner images, handwriting, diagrams

Neon Postgres 16 + pgvector   (ap-southeast-1)
```

The API Worker holds the secrets, owns the R2 binding, and answers
`/edge-health` without waking the container. Everything else is proxied to
FastAPI untouched.

## Quick start

```bash
make setup     # venvs, npm installs, .env from the example
make up        # Postgres on :5432
make migrate
make seed      # demo course, instructor@example.edu, student@example.edu
make api       # :8000
make web       # :3000
```

Both dev accounts use the password `dev-password-change-me`.

## Phase 0 is done when

A student can register, sign in, open a course, be served a question, submit an
answer, and see it stored — with an `interactions` row and a
`selection_decisions` row beside it. Migrations run forwards and backwards in
CI. `push` to `main` deploys both Workers. Nothing more.

Deliberately absent: question generation, embeddings, grading, mastery
estimation, misconception detection, feedback, multimodal upload. The tables
exist; the services return fixtures and say so.

## Four things that are load-bearing

**Grounding.** `source_documents` → `source_chunks`, joined to concepts and
questions through `concept_evidence` and `question_evidence`. A rule about not
inventing page numbers is only enforceable if every claim points at a chunk id.

**Provenance.** Every model call writes one `ai_runs` row with the prompt hash,
parameters and seed, and every artefact carries its `ai_run_id`. This holds
with `AI_ENABLED=false` too — the fixture path writes the same row, so the audit
trail is exercised from day one.

**Instrument isolation.** Fixed pre- and post-test items carry
`is_fixed_instrument`, the adaptive engine reads only the
`adaptive_question_pool` view, and three database triggers make the rule hold
even if application code forgets. A locked instrument cannot gain items, lose
items, or have its questions edited.

**Reproducibility.** Every adaptive choice writes a `selection_decisions` row
with the candidate pool, the scores, the policy version, the RNG seed and the
learner state as read at that moment. A decision you cannot replay is a
decision you cannot report.

`interactions`, `learner_state_history`, `ai_runs` and `selection_decisions`
are append-only, enforced by trigger rather than convention.

## Deploying

```bash
cd apps/api
wrangler secret put DATABASE_URL      # Neon pooled connection string
wrangler secret put JWT_SECRET        # openssl rand -base64 48
wrangler secret put AI_API_KEY        # not needed while AI_ENABLED=false
npm run deploy

cd ../web
npx wrangler kv namespace create NEXT_INC_CACHE_KV   # id goes in wrangler.jsonc
npm run deploy
```

Replace `api.example.com` and `app.example.com` in both `wrangler.jsonc` files
before the first deploy.

## Repo layout

```
apps/api      FastAPI monolith + the Worker that fronts its container
  app/core      config, logging, db, security, deps, errors, middleware
  app/models    SQLAlchemy, mirrors migrations/versions/0001_initial.py
  app/modules   auth · content · concepts · assessment · ai · learner
                · adaptive · research
  worker/       Cloudflare Worker entry point
  migrations/   Alembic
apps/web      Next.js on Workers
docs/         architecture notes, Phase 0 checklist
```

Modules talk through service functions, never by importing each other's
models. That is the seam a later split would follow.

## Documentation

- [docs/architecture.md](docs/architecture.md) — topology, the Cloudflare
  constraints that shaped it, and what to watch
- [docs/phase0-checklist.md](docs/phase0-checklist.md) — the acceptance list
