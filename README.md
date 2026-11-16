# sanaap-backend-challenge-api

REST API for the Sanaap backend challenge (Part 2 — Document Management System):
secure upload, search, update and delete of documents in MinIO, with JWT
username/password authentication and role-based access control.

Built with [Django](https://www.djangoproject.com/) and
[Django REST Framework](https://www.django-rest-framework.org/) — typed
(`mypy`), linted (`ruff`), tested (`pytest`).

## Usage — step by step

### 1. Install

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure the environment

```bash
cp .env.example .env
```

Open `.env` and adjust if needed (`SECRET_KEY`, JWT token lifetimes,
`DEFAULT_FROM_EMAIL`, …). The database defaults to **PostgreSQL** running in
Docker (next step); set `DB_ENGINE=sqlite3` for zero-setup SQLite instead.

### 3. Start the development database

```bash
docker compose -f docker-compose.dev.yml up -d
```

The **development** compose file (`docker-compose.dev.yml`, project
`dms-dev`) starts PostgreSQL and MinIO — the app runs in your venv. Redis
joins this file at its feature level. Port 5432 already taken?
Change the left side to e.g. `"5434:5432"` and set `DB_PORT=5434` in `.env`.

### 4. Create the database tables

```bash
python manage.py migrate
```

*(Not needed in production — migrations run automatically on container start.)*

### 5. Create the first admin

There is **no self-registration** — users are provisioned by an admin, so the
very first admin is created from a shell:

```bash
python manage.py shell -c "from accounts.models import User, UserRole; User.objects.create_superuser('admin', 'admin@example.com', 'secret123', role=UserRole.ADMIN)"
```

In production, run it inside the app container:

```bash
docker compose exec web python manage.py shell -c "from accounts.models import User, UserRole; User.objects.create_superuser('admin', 'admin@example.com', 'secret123', role=UserRole.ADMIN)"
```

### 6. Run the server

**Development** — app in the venv, against the dev database:

```bash
make run
```

**Production** — full stack from the default compose file (`docker-compose.yml`,
project `dms-prod`): app container (auto-migrates on start) + PostgreSQL:

```bash
docker compose up --build
```

→ http://127.0.0.1:8000

### 7. Work with the API

Log in with the admin credentials to get a JWT pair:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "secret123"}'
```

Send the returned `access` token with every protected request:

```bash
curl http://127.0.0.1:8000/api/v1/users/ \
     -H "Authorization: Bearer <access>"
```

The full endpoint list is in [API](#api) below.

### 8. Run the tests & quality gates

```bash
make check      # lint + types + tests
```

## Development & production environments

| | Development | Production |
|---|---|---|
| Compose file | `docker-compose.dev.yml` (`dms-dev`) | `docker-compose.yml` (`dms-prod`) |
| App | runs in your venv (`make run`) | `web` container from `Dockerfile` |
| Database | `postgres` container, port 5432 published | `postgres` container, internal network only |
| Migrations | `python manage.py migrate` | automatic on container start |
| Start | `docker compose -f docker-compose.dev.yml up -d` | `docker compose up --build` |
| Stop | `docker compose -f docker-compose.dev.yml down` | `docker compose down` |

The two projects are isolated (separate volumes) and can run at the same time.
Redis joins **both** files at its feature level; nginx joins the production
file. Document bytes are stored by MinIO (`STORAGE_BACKEND=minio` in `.env`;
a local-filesystem backend is available via `STORAGE_BACKEND=local` — MinIO
console: http://127.0.0.1:9001).

### Deploying to a server

Only `.env` changes per machine — the compose files are machine-independent:

```bash
git clone <repo> && cd sanaap-backend-challenge-api
cp .env.example .env
# set SECRET_KEY, DB_PASSWORD, ALLOWED_HOSTS=<your domain>
# (and WEB_PORT in .env if port 8000 is taken)
docker compose up --build -d
```

Redeploying: `git pull && docker compose up --build -d`.

### Running without Docker

Keep `DB_ENGINE=sqlite3` in `.env` — the SQLite fallback needs zero setup and
everything (`make run`, `make check`) works the same. For native PostgreSQL,
create a role/database (`CREATE USER dms WITH PASSWORD 'dms' CREATEDB;` /
`CREATE DATABASE dms OWNER dms;`) and set the `DB_*` values in `.env`.
`CREATEDB` lets Django create the automatic `test_dms` test database.

## Commands

| Command | What it does |
|---------|--------------|
| `make run` | start the dev server → http://127.0.0.1:8000 |
| `make migrate` | apply database migrations |
| `make makemigrations` | create new migrations |
| `make test` | run the test suite (pytest) |
| `make lint` | PEP 8 check (ruff) |
| `make format` | auto-format the code (ruff) |
| `make typecheck` | static type check (mypy) |
| `make check` | **all quality gates** (lint + types + tests) |
| `make help` | list all available commands |
| `docker compose -f docker-compose.dev.yml up -d` | start the dev database + MinIO |
| `docker compose up --build` | build + run the production stack |
| `docker compose logs -f web` | production app logs |
| `docker compose exec web <cmd>` | run a command in the production app |
| `docker compose down` | stop production (`-v` also wipes the db volume) |

No `make`? Plain equivalents: `python manage.py runserver`, `python manage.py migrate`,
`pytest`, `ruff check .`, `ruff format .`, `mypy .`

Tests live in `tests/` and run against an automatic throwaway test database
(`test_dms` on PostgreSQL, in-memory on SQLite) — your real data is never
touched. Run them before every push; `make check` is the full gate.

## API

Base URL: `/api/v1/`. All endpoints return JSON.

**Interactive documentation:** Swagger UI at `/api/docs/` — try every endpoint
with the **Authorize** button (paste a Bearer token from login). Raw OpenAPI
schema at `/api/schema/`.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/login/` | — | obtain JWT access + refresh pair |
| POST | `/api/v1/auth/refresh/` | — | get a fresh access token |
| POST | `/api/v1/auth/logout/` | Bearer | blacklist the refresh token |
| POST | `/api/v1/auth/password-reset/` | — | request a reset link by email |
| POST | `/api/v1/auth/password-reset/confirm/` | — | set a new password (uid + token) |
| GET | `/api/v1/users/` | admin | list users |
| POST | `/api/v1/users/` | admin | create a user (with role) |
| PATCH | `/api/v1/users/<id>/role/` | admin | change a user's role |
| POST | `/api/v1/documents/` | Bearer | upload a document (multipart: file, title, description) |
| GET | `/api/v1/documents/` | Bearer | list documents (filter + pagination) |
| GET | `/api/v1/documents/<id>/` | Bearer | document metadata |
| PATCH | `/api/v1/documents/<id>/` | Bearer | update title, description and/or file |
| DELETE | `/api/v1/documents/<id>/` | Bearer | delete document + stored file |
| GET | `/api/v1/documents/<id>/download/` | Bearer | download the file |
| GET | `/api/v1/documents/<id>/url/` | Bearer | presigned download URL (1 hour) |

Authenticate by sending `Authorization: Bearer <access>` on protected
endpoints. Auth endpoints are rate-limited (5 requests/minute per client).
`GET /api/v1/documents/<id>/url/` returns a time-limited presigned URL so
clients can fetch the file directly from MinIO without proxying through the
app.

`GET /api/v1/documents/` supports filtering (`?title=`, `?content_type=`,
`?uploaded_by=`, `?created_after=`, `?created_before=` — ISO dates, inclusive) and
pagination (`?page=`, `?page_size=` — default 10, max 100). List responses
are wrapped as `{count, next, previous, results}`.

### Roles

| Role | Can |
|------|-----|
| `admin` | everything — user management, upload, update, delete, download |
| `editor` | upload and update documents/images; download — **no delete** |
| `viewer` | list and download documents only |

## How the project is built — level by level

| Level | Branch | What it adds |
|-------|--------|--------------|
| 1 | `develop` | project bootstrap, env-driven settings |
| 2 | `feature/database-repositories` | user & document models, repository pattern (Protocol + Django ORM) |
| 3 | `feature/auth-user-management` | JWT auth, password reset, user management |
| 4 | `feature/docker-deployment` | dev/prod Docker Compose + PostgreSQL integration |
| 5 | `feature/swagger-readme` | Swagger UI + OpenAPI docs (`drf-spectacular`) |
| 6 | `feature/documents-api-minio` | document CRUD + MinIO storage (Facade, Singleton) |
| 7 | `feature/rbac-secure-urls` | role policies + presigned URLs (Strategy) |
| 8 | `feature/filter-pagination` | filtering & pagination |
| 9 | `feature/background-tasks` | Celery background tasks (Redis joins Compose) |
| 10 | `feature/audit-logging` | audit logging (Observer) |
| 11 | `feature/nginx-gunicorn` | production serving |
| 12 | `feature/websocket-notifications` | WebSocket notifications (Channels) |
| 13 | `feature/final-qa` | coverage gate, release to `main` (`v1.0.0`) |

## Project structure

- `config/` — Django project (settings, urls)
- `accounts/` — user model with roles; JWT auth, password reset and user
  management (views, serializers, services)
- `documents/` — model, repository (Protocol + ORM adapter), storage backends
  (MinIO/local behind a Protocol), validation, role policies (Strategy),
  service layer, API
- `tests/` — pytest suite
- `docker-compose.yml` — production: app + PostgreSQL + MinIO (nginx-ready)
- `docker-compose.dev.yml` — development: PostgreSQL + MinIO (app runs in
  venv; Redis joins later)
- `Dockerfile` / `entrypoint.sh` — container image with auto-migrations

## References

- [Django](https://www.djangoproject.com/) ·
  [Django REST Framework](https://www.django-rest-framework.org/) ·
  [SimpleJWT](https://django-rest-framework-simplejwt.readthedocs.io/)
- [pytest-django](https://pytest-django.readthedocs.io/) ·
  [ruff](https://docs.astral.sh/ruff/) ·
  [mypy](https://mypy.readthedocs.io/)
