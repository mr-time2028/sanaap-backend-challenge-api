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
`DEFAULT_FROM_EMAIL`, …).

### 3. Create the database tables

```bash
python manage.py migrate
```

### 4. Create the first admin

There is **no self-registration** — users are provisioned by an admin, so the
very first admin is created from a shell:

```bash
python manage.py shell -c "from accounts.models import User, UserRole; User.objects.create_superuser('admin', 'admin@example.com', 'secret123', role=UserRole.ADMIN)"
```

### 5. Run the server

```bash
make run        # or: python manage.py runserver
```

→ http://127.0.0.1:8000

### 6. Work with the API

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

### 7. Run the tests & quality gates

```bash
make check      # lint + types + tests
```

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

No `make`? Plain equivalents: `python manage.py runserver`, `python manage.py migrate`,
`pytest`, `ruff check .`, `ruff format .`, `mypy .`

Tests live in `tests/` and run against an automatic throwaway test database
(SQLite by default) — your data is never touched and no external services are
needed. Run them before every push; `make check` is the full gate.

## API

Base URL: `/api/v1/`. All endpoints return JSON.

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

Authenticate by sending `Authorization: Bearer <access>` on protected
endpoints. Auth endpoints are rate-limited (5 requests/minute per client).

### Roles

| Role | Can |
|------|-----|
| `admin` | everything — incl. user management and deleting documents |
| `editor` | upload and update documents/images |
| `viewer` | download documents only |

## How the project is built — level by level

| Level | Branch | What it adds |
|-------|--------|--------------|
| 1 | `develop` | project bootstrap, env-driven settings |
| 2 | `feature/database-repositories` | user & document models, repository pattern (Protocol + Django ORM) |
| 3 | `feature/auth-user-management` | JWT auth, password reset, user management |
| 4 | `feature/postgresql` | PostgreSQL (env-driven, SQLite fallback) |
| 5 | `feature/documents-api-minio` | document CRUD + MinIO storage (Facade, Singleton) |
| 6 | `feature/rbac-secure-urls` | role policies + presigned URLs (Strategy) |
| 7 | `feature/filter-pagination` | filtering & pagination |
| 8 | `feature/swagger-readme` | OpenAPI/Swagger documentation |
| 9 | `feature/docker-deployment` | Docker Compose (Django/PostgreSQL/Redis/MinIO) |
| 10 | `feature/background-tasks` | Celery background tasks |
| 11 | `feature/audit-logging` | audit logging (Observer) |
| 12 | `feature/nginx-gunicorn` | production serving |
| 13 | `feature/websocket-notifications` | WebSocket notifications (Channels) |
| 14 | `feature/final-qa` | coverage gate, release to `main` (`v1.0.0`) |

## Project structure

- `config/` — Django project (settings, urls)
- `accounts/` — user model with roles; JWT auth, password reset and user
  management (views, serializers, services)
- `documents/` — document model + repository (Protocol + Django ORM adapter)
- `tests/` — pytest suite

## References

- [Django](https://www.djangoproject.com/) ·
  [Django REST Framework](https://www.django-rest-framework.org/) ·
  [SimpleJWT](https://django-rest-framework-simplejwt.readthedocs.io/)
- [pytest-django](https://pytest-django.readthedocs.io/) ·
  [ruff](https://docs.astral.sh/ruff/) ·
  [mypy](https://mypy.readthedocs.io/)
