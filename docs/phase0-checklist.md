# Phase 0 checklist

## Repository
- [ ] Git repo initialised, `main` protected, PRs required
- [ ] `.env.example` committed; no real secret anywhere in history
- [ ] `make setup` works from a clean clone

## Database
- [ ] Neon project created in `ap-southeast-1`, pgvector enabled
- [ ] `alembic upgrade head` applies cleanly
- [ ] `alembic downgrade base` then `upgrade head` also applies cleanly
- [ ] Append-only triggers verified: `UPDATE interactions` raises
- [ ] Instrument triggers verified: a non-fixed question cannot join an
      instrument, and a locked instrument rejects changes

## Backend
- [ ] `/health` responds without touching the database
- [ ] `/health/ready` fails loudly when the database is unreachable
- [ ] Register, login, refresh, logout, `/auth/me` all work
- [ ] Refresh token is httpOnly, `Secure` in production, scoped to `/auth`
- [ ] Every response carries `x-request-id`
- [ ] Logs are single-line JSON outside local development

## Frontend
- [ ] Sign in, list courses, start a session, answer a question
- [ ] The interface states that answers are recorded but not marked
- [ ] Keyboard focus is visible throughout
- [ ] Usable at 380px wide

## Cloudflare
- [ ] `wrangler deploy` succeeds for `adaptive-api`, container image builds
- [ ] `wrangler deploy` succeeds for `adaptive-web`
- [ ] Secrets set: `DATABASE_URL`, `JWT_SECRET`
- [ ] KV namespace created and its id written into `apps/web/wrangler.jsonc`
- [ ] R2 buckets created for production and preview
- [ ] Custom domains resolve and serve
- [ ] Cloudflare Access gates the preview environment
- [ ] Cold start measured from the pilot's actual location and written down

## Pipeline
- [ ] CI runs lint, migrations both directions, tests, and a docker build
- [ ] Deploy runs migrations before shipping the image
- [ ] Smoke checks hit `/edge-health`, `/health`, `/health/ready`, and the web root

## Before Phase 1
- [ ] AI Gateway configured with a hard spend cap, even though `AI_ENABLED=false`
- [ ] Log shipping to a service that retains longer than a week
- [ ] Backups confirmed on Neon, restore tested once
- [ ] Ethics approval reference recorded on the `studies` row
