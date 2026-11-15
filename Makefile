.DEFAULT_GOAL := help

.PHONY: help test lint format typecheck check run migrate makemigrations

help:  ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

test:  ## Run the test suite
	pytest

lint:  ## Check code style (PEP 8)
	ruff check .

format:  ## Auto-format the code
	ruff format .

typecheck:  ## Static type checking
	mypy .

check: lint typecheck test  ## Run all quality gates (lint + types + tests)

run:  ## Start the dev server locally
	python manage.py runserver

migrate:  ## Apply database migrations
	python manage.py migrate

makemigrations:  ## Create new migrations
	python manage.py makemigrations
