# sanaap-backend-challenge-api

## Getting started

Requirements: Python 3.10+, `make` (optional but recommended).

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # adjust values if needed
python manage.py migrate
```

## Usage — run the project

| Command | What it does |
|---------|--------------|
| `make run` | start the dev server → http://127.0.0.1:8000 |
| `make migrate` | apply database migrations |
| `make makemigrations` | create new migrations |
| `make help` | list all available commands |

No `make`? Plain equivalents: `python manage.py runserver`, `python manage.py migrate`, …

## Usage — tests & quality

| Command | What it does |
|---------|--------------|
| `make test` | run the test suite (pytest) |
| `make lint` | PEP 8 check (ruff) |
| `make format` | auto-format the code (ruff) |
| `make typecheck` | static type check (mypy) |
| `make check` | **all quality gates** (lint + types + tests) |

No `make`? Plain equivalents: `pytest`, `ruff check .`, `ruff format .`, `mypy .`

Tests live in `tests/` and run against the project's SQLite database by default —
no services needed. Run them before every push; `make check` is the full gate.

## Project structure

- `config/` — Django project (settings, urls)
- `accounts/` — custom user model with RBAC role
- `documents/` — document model + repository (Protocol + Django ORM adapter)
- `tests/` — pytest suite
