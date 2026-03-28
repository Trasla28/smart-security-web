.PHONY: dev test migrate seed lint build

dev:
	docker compose -f docker-compose.yml up --build

dev-down:
	docker compose -f docker-compose.yml down

test:
	docker compose -f docker-compose.yml run --rm backend pytest tests/ -v --cov=app --cov-report=term-missing

migrate:
	docker compose -f docker-compose.yml run --rm backend alembic upgrade head

migrate-down:
	docker compose -f docker-compose.yml run --rm backend alembic downgrade -1

seed:
	docker compose -f docker-compose.yml run --rm backend python scripts/seed.py

lint:
	docker compose -f docker-compose.yml run --rm backend ruff check app/ && ruff format --check app/
	docker compose -f docker-compose.yml run --rm frontend npm run lint

build:
	docker compose -f docker-compose.prod.yml build

logs:
	docker compose -f docker-compose.yml logs -f

shell-backend:
	docker compose -f docker-compose.yml exec backend bash

shell-db:
	docker compose -f docker-compose.yml exec db psql -U tickets_user -d tickets_db
