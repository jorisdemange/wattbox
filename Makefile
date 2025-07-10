.PHONY: help dev prod stop clean install test lint

help:
	@echo "WattBox Development Commands:"
	@echo "  make dev      - Start development environment"
	@echo "  make prod     - Start production environment"
	@echo "  make stop     - Stop all services"
	@echo "  make clean    - Clean up containers and volumes"
	@echo "  make install  - Install dependencies locally"
	@echo "  make test     - Run tests"
	@echo "  make lint     - Run linters"

dev:
	docker-compose -f docker-compose.dev.yml up

prod:
	docker-compose up -d

stop:
	docker-compose down
	docker-compose -f docker-compose.dev.yml down

clean:
	docker-compose down -v
	docker-compose -f docker-compose.dev.yml down -v
	rm -rf backend/__pycache__
	rm -rf backend/.pytest_cache
	rm -rf frontend/node_modules
	rm -rf frontend/dist

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

test:
	cd backend && pytest
	cd frontend && npm run test:unit

lint:
	cd backend && python -m flake8 .
	cd frontend && npm run lint

build:
	docker-compose build

logs:
	docker-compose logs -f

backend-shell:
	docker-compose exec backend /bin/bash

db-shell:
	docker-compose exec db psql -U wattbox -d wattbox