# Porfacan

Porfacan is a digital archive and crowdsourced lexicon of Iranian opposition slang and dissent (2009-2026). The project is built with Django SSR, PostgreSQL, Celery, Redis, RabbitMQ, and S3-compatible media storage.

## Stack

- Django 5.x (templates, RTL-first UI)
- PostgreSQL (search-ready schema with GIN index hooks)
- Redis (cache + sessions)
- RabbitMQ + Celery + Celery Beat
- Amazon S3 via `django-storages`
- Arweave integration hooks for permanent archiving

## Quickstart (Docker Compose)

1. Copy environment variables:
   - `cp .env.example .env`
2. Build and start services:
   - `docker compose up --build`
3. Run migrations:
   - `docker compose exec web python manage.py migrate`
4. Create admin user:
   - `docker compose exec web python manage.py createsuperuser`
5. Open:
   - `http://localhost:8000`

## Local Development (without Docker)

1. Create and activate virtualenv.
2. Install dependencies:
   - `pip install -r requirements/local.txt`
3. Ensure PostgreSQL, Redis, RabbitMQ are running.
4. Set env values using `.env.example`.
5. Run migrations and server:
   - `python manage.py migrate`
   - `python manage.py runserver`

## Project Layout

- `config/` Django project config and split settings (`base.py`, `local.py`, `production.py`)
- `apps/` domain apps (`lexicon`, `users`, `archiver`, `api`)
- `templates/` global templates with RTL base
- `static/` CSS and font assets
- `requirements/` split dependency files
- `docs/` contributor and API docs

## Tests

- Run tests:
  - `pytest`
- Current baseline includes ranking algorithm tests for lexicon hot sorting.
