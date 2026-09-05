# Running on Windows

The backend runs inside Docker, so you do not need Python installed on
Windows at all. Your Python 3.14 stays out of the way, and the container uses
3.12 with Linux wheels for everything.

You need: **Docker Desktop** (running), **Node.js**, and **Make**.

## Setup

Open Command Prompt in the project folder.

```cmd
make setup
```

Builds the API image and installs frontend packages. First run takes two or
three minutes. It also creates `.env` from the example.

## Start

```cmd
make up
make migrate
make seed
```

`make up` starts Postgres and the API. `make migrate` creates the 27 tables and
the triggers. `make seed` loads the demo course.

Wait about five seconds between `make up` and `make migrate` — Postgres needs a
moment to accept connections. If `make migrate` says "connection refused", just
run it again.

Then in a second Command Prompt window:

```cmd
make web
```

## Check it works

| What | Where |
|---|---|
| API health | http://localhost:8000/health |
| API docs | http://localhost:8000/docs |
| App | http://localhost:3000 |

Sign in at http://localhost:3000/login as `student@example.edu` with the
password `dev-password-change-me`.

## Day to day

```cmd
make up          start
make logs        watch the API logs
make down        stop
make shell       shell inside the API container
make psql        database shell
make test        run the test suite
make reset       wipe the database and start over
```

Editing anything under `apps\api\app` reloads the server automatically. You do
not need to rebuild unless you change `pyproject.toml` or the `Dockerfile`, in
which case run `docker compose build api`.

## If something breaks

**`docker: error during connect`** — Docker Desktop is not running. Start it
from the Start menu and wait for the whale icon to stop animating.

**`make migrate` says connection refused** — Postgres is still starting. Wait
five seconds and run it again.

**Port 5432 or 8000 already in use** — something else is on that port. Find it
with `netstat -ano | findstr :5432`, or change the port in `docker-compose.yml`.

**Changes to `app` are not picked up** — check `make logs` for a syntax error.
A crashed reload leaves the old code running.

**Fresh start** — `make reset` drops the database volume and starts clean, then
run `make migrate` and `make seed` again.

## Only if you want Python locally

You do not need this for development. If you want editor autocomplete and type
checking against the real packages, install **Python 3.12** (not 3.14 — several
of these packages have no 3.14 wheels yet) and then:

```cmd
cd apps\api
py -3.12 -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
```

Point your editor at `apps\api\.venv\Scripts\python.exe`. Keep running the
actual server through Docker.

## Only when you deploy to Cloudflare

The npm packages under `apps\api` are for the Cloudflare Worker and are not
needed until you deploy.

```cmd
cd apps\api
npm install
```
