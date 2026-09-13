# tshortner

A URL shortener built with FastAPI, SQLModel (Postgres), and Redis.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package/project manager)
- Docker (for local Postgres and Redis)

## Quick start

1. **Install dependencies**

   ```bash
   uv sync
   ```

2. **Configure environment** (optional — defaults already match the `docker-compose.yml` services below)

   ```bash
   cp .env.example .env
   ```

3. **Start Postgres and Redis**

   ```bash
   docker compose up -d
   ```

4. **Run database migrations**

   ```bash
   uv run alembic upgrade head
   ```

5. **Start the app**

   ```bash
   uv run fastapi dev main.py
   ```

   The API is now available at http://127.0.0.1:8000, with interactive docs at
   http://127.0.0.1:8000/docs.

6. **Try it out**

   ```bash
   curl -X POST http://127.0.0.1:8000/urls \
     -H "Content-Type: application/json" \
     -d '{"original_url": "https://example.com/some/very/long/path", "user_id": "user-1"}'

   curl -i http://127.0.0.1:8000/health
   ```

## Short codes

Codes are random base62 strings, `SHORT_CODE_LENGTH` characters long (default 7). Every code an
instance generates starts with one of its `SHORT_CODE_PREFIXES` (comma-separated single characters,
default: any). Give each instance a disjoint set — say `a,b,c` and `A,B,C` — and instances can never
generate the same code. A new code is checked against both active and expired codes, so an expired
link never starts pointing somewhere else.

## Running tests

Tests run against an in-memory SQLite database and a fake Redis client, so
Postgres/Redis don't need to be running.

```bash
uv run pytest
```

## Useful commands

| Command | Description |
|---|---|
| `uv run alembic revision --autogenerate -m "message"` | Generate a new migration from model changes |
| `uv run alembic downgrade -1` | Roll back the last migration |
| `docker compose down` | Stop Postgres and Redis |
| `docker compose down -v` | Stop Postgres and Redis, and delete data volumes |

## Project structure

```
src/tshortner/
├── api/          # FastAPI routers, endpoints, and dependencies
├── core/         # Settings
├── db/           # Postgres and Redis clients
├── middleware/   # Publishes short-link usage to Redis pub/sub
├── models/       # SQLModel tables
├── repositories/ # Database queries
├── schemas/      # Request/response models
├── services/     # Shortening and cached lookups
├── utils/        # Short code generation
└── worker/       # Background threads: access-log flushing and link expiry

alembic/          # Database migrations
tests/
├── unit/         # Pure logic tests (no I/O)
├── integration/  # Repository/DB tests
└── api/          # End-to-end HTTP tests
```
