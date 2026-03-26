# Porfacan

Porfacan is a digital archive and crowdsourced lexicon of Iranian opposition slang and dissent. The project is built with Django SSR, PostgreSQL, Celery, Redis, RabbitMQ, and S3-compatible media storage.

## Stack

- Django 5.x (templates, RTL-first UI)
- PostgreSQL (search-ready schema with GIN index hooks)
- Redis (cache + sessions)
- RabbitMQ + Celery + Celery Beat
- Amazon S3 via `django-storages`
- Arweave integration hooks for permanent archiving

## Quickstart (Docker Compose)

- Development compose file: `docker-compose.dev.yml`
- Production compose file: `docker-compose.yml`

1. Copy environment variables:
   - `cp .env.example .env`
2. Bootstrap development dependencies (creates databases and RabbitMQ user/vhost idempotently):
   - `./scripts/dev/bootstrap.sh`
3. Build and start services:
   - `docker compose -f docker-compose.dev.yml up --build`
4. Run migrations:
   - `docker compose -f docker-compose.dev.yml exec web python manage.py migrate`
5. Create admin user:
   - `docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser`
6. Open:
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

## Documentation

- Contributor guide: [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)
- API notes: [`docs/API.md`](docs/API.md)
- Content license and terms: [`docs/CONTENT_LICENSE.md`](docs/CONTENT_LICENSE.md)

## Open Source and Crowdsourcing Model

- Porfacan is open source for code contributions and crowdsourced for public lexicon content.
- Code contributions are governed by the `MIT` License in [`LICENSE`](LICENSE).
- Public website content contributions are governed by `CC BY-SA 4.0` terms in [`docs/CONTENT_LICENSE.md`](docs/CONTENT_LICENSE.md).
- Contributors should review both licenses before submitting code or content.

## Tests

- Run tests:
  - `pytest`
- Current baseline includes ranking algorithm tests for lexicon hot sorting.
