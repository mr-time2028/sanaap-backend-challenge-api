# sanaap-backend-challenge-api

## Contents

- [Development and production environments](#development-and-production-environments)
- [Development usage](#development-usage)
  - [1. Install the dependencies](#1-install-the-dependencies)
  - [2. Configure the environment](#2-configure-the-environment)
  - [3. Start the backing services](#3-start-the-backing-services)
  - [4. Create the database tables](#4-create-the-database-tables)
  - [5. Create the first admin](#5-create-the-first-admin)
  - [6. Run the server](#6-run-the-server)
  - [7. Work with the API](#7-work-with-the-api)
  - [8. Run the tests & quality gates](#8-run-the-tests--quality-gates)
  - [Development without Docker](#development-without-docker)
- [Production usage](#production-usage)
  - [1. Configure the environment](#1-configure-the-environment)
  - [2. Build and start the stack](#2-build-and-start-the-stack)
  - [3. Create the first admin](#3-create-the-first-admin)
  - [4. Work with the API](#4-work-with-the-api)
  - [Deploying to a server](#deploying-to-a-server)
  - [HTTPS](#https)
- [Commands](#commands)
- [API](#api)
  - [Roles](#roles)
- [How the project is built — level by level](#how-the-project-is-built--level-by-level)
- [Project structure](#project-structure)
- [References](#references)

REST API for the Sanaap backend challenge (Part 2 — Document Management System):
secure upload, search, update and delete of documents in MinIO, with JWT
username/password authentication and role-based access control.

Built with [Django](https://www.djangoproject.com/) and
[Django REST Framework](https://www.django-rest-framework.org/) — typed
(`mypy`), linted (`ruff`), tested (`pytest`).

## Development and production environments

The project runs in two modes. **Each mode has its own usage section below —
follow only the one you need.**

| Mode | What runs where | Usage section |
|------|-----------------|---------------|
| **Development** | the Django app runs **on your machine** (virtualenv); Docker is used only for the backing services (PostgreSQL, MinIO, Redis) | [Development usage](#development-usage) |
| **Production** | **everything runs in Docker**: nginx → gunicorn app container + Celery worker + PostgreSQL + MinIO + Redis | [Production usage](#production-usage) |

| | Development | Production |
|---|---|---|
| Compose file | `docker-compose.dev.yml` (`dms-dev`) | `docker-compose.yml` (`dms-prod`) |
| App | runs in your venv (`make run`) | `web` container (gunicorn) behind `nginx` |
| Background worker | by hand, second terminal: `celery -A config worker -l info` | `worker` container — compose runs the same command for you |
| Entry point | http://127.0.0.1:8000 | http://localhost:8080 (`NGINX_PORT`) |
| Database | `postgres` container, port 5432 published | `postgres` container, internal network only |
| Migrations | `python manage.py migrate` | automatic on container start |
| Start | `docker compose -f docker-compose.dev.yml up -d` | `docker compose up --build` |
| Stop | `docker compose -f docker-compose.dev.yml down` | `docker compose down` |

The two projects are isolated (separate volumes) and can run at the same
time. In production, nginx is the only public entry point: it proxies to
gunicorn, serves `/static/`, and upgrades WebSocket connections. Document
bytes are stored by MinIO (`STORAGE_BACKEND=minio` in `.env`; a
local-filesystem backend is available via `STORAGE_BACKEND=local` — MinIO
console: http://127.0.0.1:9001).

## Development usage

Follow these steps top to bottom. The app runs in a virtualenv on your
machine; Docker runs only the backing services.

### 1. Install the dependencies

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
`DEFAULT_FROM_EMAIL`, …). Generate a real secret key with
`python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(50))"`
(alphanumeric + `-_` only — quotes and `#`/`$` break `.env` parsing).

The database defaults to **PostgreSQL in Docker** (started in step 3). Set
`DB_ENGINE=sqlite3` for a zero-setup database instead.

### 3. Start the backing services

Start PostgreSQL, MinIO and Redis in Docker (the app itself is **not**
containerized in development):

```bash
docker compose -f docker-compose.dev.yml up -d
```

The development compose file (`docker-compose.dev.yml`, project `dms-dev`)
publishes PostgreSQL on port 5432. Port already taken? Change the left side
to e.g. `"5434:5432"` and set `DB_PORT=5434` in `.env`.

### 4. Create the database tables

```bash
python manage.py migrate
```

### 5. Create the first admin

There is **no self-registration** — users are provisioned by an admin, so
the very first admin is created from a shell:

```bash
python manage.py shell -c "from accounts.models import User, UserRole; User.objects.create_superuser('admin', 'admin@example.com', 'secret123', role=UserRole.ADMIN)"
```

### 6. Run the server

Run the app and the background worker — one command per terminal:

```bash
make run
```

```bash
celery -A config worker -l info
```

→ http://127.0.0.1:8000

### 7. Work with the API

Log in to get a JWT pair:

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

Tests use a throwaway test database — your real data is never touched.

### Development without Docker

Keep `DB_ENGINE=sqlite3` in `.env` — the SQLite fallback needs zero setup and
everything (`make run`, `make check`) works the same. For native PostgreSQL,
create a role/database (`CREATE USER dms WITH PASSWORD 'dms' CREATEDB;` /
`CREATE DATABASE dms OWNER dms;`) and set the `DB_*` values in `.env`.
`CREATEDB` lets Django create the automatic `test_dms` test database.

## Production usage

Follow these steps top to bottom. Everything runs in Docker — no Python or
virtualenv is needed on the machine.

### 1. Configure the environment

```bash
cp .env.example .env
```

Open `.env` and set at least `SECRET_KEY`, `DB_PASSWORD` and
`ALLOWED_HOSTS=<your domain>`. Generate a real secret key with
`python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(50))"`
(alphanumeric + `-_` only — quotes and `#`/`$` break `.env` parsing).
Set `NGINX_PORT` in `.env` if port 8080 is taken.

### 2. Build and start the stack

```bash
docker compose up --build -d
```

This builds the image (installing `requirements.txt` inside it) and starts
the full stack — one container per service:

- `nginx` — the only entry point (reverse proxy, static files, WebSockets)
- `web` — the Django app under gunicorn (migrations run automatically on
  start — no manual `migrate` needed)
- `worker` — the Celery background worker: **you never run it by hand** —
  this container runs `celery -A config worker -l info` for you (its
  `command:` is defined in `docker-compose.yml`) and listens on the Redis
  broker (`CELERY_BROKER_URL=redis://redis:6379/0`) for background jobs
  such as checksum computation
- `postgres`, `minio`, `redis` — the backing services

Check the worker with `docker compose logs -f worker`.

→ http://localhost:8080 — nginx is the only entry point (`NGINX_PORT` in `.env`)

### 3. Create the first admin

There is **no self-registration** — create the first admin inside the
running app container:

```bash
docker compose exec web python manage.py shell -c "from accounts.models import User, UserRole; User.objects.create_superuser('admin', 'admin@example.com', 'secret123', role=UserRole.ADMIN)"
```

### 4. Work with the API

The API is the same as in development — through nginx at
`http://localhost:8080`:

```bash
curl -X POST http://localhost:8080/api/v1/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "secret123"}'
```

Send the returned `access` token with every protected request:

```bash
curl http://localhost:8080/api/v1/users/ \
     -H "Authorization: Bearer <access>"
```

The full endpoint list is in [API](#api) below. Swagger UI:
http://localhost:8080/api/docs/

Stop the stack with `docker compose down` (`-v` also wipes the volumes).

### Deploying to a server

Only `.env` changes per machine — the compose files are machine-independent:

```bash
git clone <repo> && cd sanaap-backend-challenge-api
cp .env.example .env
# set SECRET_KEY, DB_PASSWORD, ALLOWED_HOSTS=<your domain>
docker compose up --build -d
```

Redeploying: `git pull && docker compose up --build -d`.

### HTTPS

Point DNS at the server, then `certbot --nginx -d yourdomain.com` —
TLS terminates at nginx (the ready-made 443 block is in `nginx/nginx.conf`).
Afterwards flip `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True` and
`CSRF_COOKIE_SECURE=True` in `.env` (keep them `False` for local HTTP —
otherwise Django redirects forever), and set
`CSRF_TRUSTED_ORIGINS=https://yourdomain.com` (the local default
`http://localhost:8080` keeps session-form logins working behind the proxy).

## Commands

| Command | Mode | What it does |
|---------|------|--------------|
| `make run` | development | start the dev server → http://127.0.0.1:8000 |
| `celery -A config worker -l info` | development | run the background worker |
| `make migrate` | development | apply database migrations |
| `make makemigrations` | development | create new migrations |
| `make test` | development | run the test suite (pytest) |
| `make lint` | development | PEP 8 check (ruff) |
| `make format` | development | auto-format the code (ruff) |
| `make typecheck` | development | static type check (mypy) |
| `make check` | development | **all quality gates** (lint + types + tests) |
| `make coverage` | development | run the tests with a coverage report (fails below 90 %) |
| `make help` | development | list all available commands |
| `docker compose -f docker-compose.dev.yml up -d` | development | start PostgreSQL + MinIO + Redis |
| `docker compose -f docker-compose.dev.yml down` | development | stop the dev backing services |
| `docker compose up --build` | production | build + run the full stack (nginx at :8080) |
| `docker compose logs -f web` | production | app logs |
| `docker compose logs -f nginx` | production | proxy logs |
| `docker compose logs -f worker` | production | Celery background worker logs |
| `docker compose exec web <cmd>` | production | run a command inside the app container |
| `docker compose down` | production | stop the stack (`-v` also wipes the volumes) |

No `make`? Plain equivalents (development): `python manage.py runserver`,
`python manage.py migrate`, `pytest`, `ruff check .`, `ruff format .`, `mypy .`

Tests live in `tests/` and run against an automatic throwaway test database
(`test_dms` on PostgreSQL, in-memory on SQLite) — your real data is never
touched. Run them before every push; `make check` is the full gate.

## API

Base URL: `/api/v1/`. All endpoints return JSON. The API works the same in
development and production — only the host changes (see step 4 of each
usage section).

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
| GET | `/api/v1/audit-logs/` | admin | audit trail — every document change with actor and diff |

Authenticate by sending `Authorization: Bearer <access>` on protected
endpoints. Auth endpoints are rate-limited (5 requests/minute per client).
`GET /api/v1/documents/<id>/url/` returns a time-limited presigned URL so
clients can fetch the file directly from MinIO without proxying through the
app.

`GET /api/v1/documents/` supports filtering (`?title=`, `?content_type=`,
`?uploaded_by=`, `?created_after=`, `?created_before=` — ISO dates, inclusive) and
pagination (`?page=`, `?page_size=` — default 10, max 100). List responses
are wrapped as `{count, next, previous, results}`.

Uploads are processed in the background: a Celery worker computes the file's
SHA-256 checksum, which appears in the document metadata (`checksum`) shortly
after the upload (immediately in tests).

Every document change is recorded in an **audit trail** (`action`, actor,
document snapshot, change diff, timestamp) — readable by admins at
`GET /api/v1/audit-logs/`. It is built with the Observer pattern: services
publish document events, and the audit recorder subscribes (the WebSocket
notifications subscribe to the same events).

**Real-time notifications:** connect to
`ws://localhost:8080/ws/documents/?token=<access>` (authenticated WebSocket)
and every document create/update/delete arrives as JSON:
`{action, document_id, document_title, username, changes}`. Built with
Django Channels; the dev/test channel layer is in-memory, production shares a
Redis channel layer across workers.

### Roles

| Role | Can |
|------|-----|
| `admin` | everything — user management, audit log, upload, update, delete, download |
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
| 11 | `feature/nginx-gunicorn` | nginx reverse proxy + gunicorn |
| 12 | `feature/websocket-notifications` | WebSocket notifications (Channels) |

## Project structure

- `config/` — Django project (settings, urls, Celery app, shared pagination,
  WebSocket auth middleware, ASGI routing)
- `accounts/` — user model with roles; JWT auth, password reset and user
  management (views, serializers, services)
- `documents/` — model, repository (Protocol + ORM adapter), storage backends
  (MinIO/local behind a Protocol), validation, role policies (Strategy),
  domain events (Observer seam), WebSocket consumer, service layer, API
- `audit/` — audit trail model + Observer recorder (who changed what, when)
- `tests/` — pytest suite
- `docker-compose.yml` — production: nginx + app + worker + PostgreSQL +
  MinIO + Redis
- `docker-compose.dev.yml` — development: PostgreSQL + MinIO + Redis (app
  runs in venv)
- `nginx/nginx.conf` — reverse proxy: gunicorn + static files
- `Dockerfile` / `entrypoint.sh` — container image (gunicorn; auto-migrations
  + static collection)

## References

- [Django](https://www.djangoproject.com/) ·
  [Django REST Framework](https://www.django-rest-framework.org/) ·
  [SimpleJWT](https://django-rest-framework-simplejwt.readthedocs.io/)
- [pytest-django](https://pytest-django.readthedocs.io/) ·
  [ruff](https://docs.astral.sh/ruff/) ·
  [mypy](https://mypy.readthedocs.io/)
