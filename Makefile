.PHONY: help install install-dev test test-cov lint format clean run-server run-simulator docs

.DEFAULT_GOAL := help

PROJECT_NAME = dronesphere
PYTHON = python3
POETRY = poetry
PYTEST = pytest
BLACK = black
ISORT = isort
FLAKE8 = flake8
MYPY = mypy

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	$(POETRY) install --only main

install-dev: ## Install all dependencies including dev
	$(POETRY) install

test: ## Run tests
	$(POETRY) run $(PYTEST) tests/unit -v

test-all: ## Run all tests with coverage
	$(POETRY) run $(PYTEST) -v --cov=src --cov-report=term-missing

lint: ## Run linting checks
	$(POETRY) run $(FLAKE8) src tests
	$(POETRY) run $(MYPY) src

format: ## Format code
	$(POETRY) run $(ISORT) src tests
	$(POETRY) run $(BLACK) src tests

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .coverage htmlcov .pytest_cache .mypy_cache dist build *.egg-info

setup: install-dev ## Initial project setup
	$(POETRY) run pre-commit install
	cp .env.example .env
	@echo "Setup complete! Edit .env file with your configuration."

run-server: ## Run the API server
	$(POETRY) run uvicorn src.adapters.input.api.rest.main:app --reload --host 0.0.0.0 --port 8000

docs-serve: ## Serve documentation locally
	$(POETRY) run mkdocs serve

docs-build: ## Build documentation
	$(POETRY) run mkdocs build

# Docker commands
docker-up: ## Start all services with docker-compose
	docker-compose -f deploy/docker/docker-compose.yaml up -d

docker-down: ## Stop all services
	docker-compose -f deploy/docker/docker-compose.yaml down

docker-logs: ## View logs for all services
	docker-compose -f deploy/docker/docker-compose.yaml logs -f

docker-ps: ## List running containers
	docker-compose -f deploy/docker/docker-compose.yaml ps

docker-restart: ## Restart all services
	docker-compose -f deploy/docker/docker-compose.yaml restart

simulator-up: ## Start PX4 simulator
	docker-compose -f deploy/docker/simulator-compose.yaml up -d

simulator-down: ## Stop PX4 simulator
	docker-compose -f deploy/docker/simulator-compose.yaml down

simulator-logs: ## View simulator logs
	docker-compose -f deploy/docker/simulator-compose.yaml logs -f

docker-clean: ## Clean up Docker resources
	docker-compose -f deploy/docker/docker-compose.yaml down -v
	docker-compose -f deploy/docker/simulator-compose.yaml down -v
	docker system prune -f

docker-db-shell: ## Connect to PostgreSQL shell
	docker exec -it dronesphere-postgres psql -U dronesphere -d dronesphere

docker-redis-cli: ## Connect to Redis CLI
	docker exec -it dronesphere-redis redis-cli

docker-test: ## Test all connections
	@echo "Testing Docker services..."
	@docker exec dronesphere-postgres pg_isready -U dronesphere -d dronesphere && echo "✅ PostgreSQL: OK" || echo "❌ PostgreSQL: FAILED"
	@docker exec dronesphere-redis redis-cli ping > /dev/null && echo "✅ Redis: OK" || echo "❌ Redis: FAILED"
	@curl -s -u dronesphere:dronesphere_pass_dev http://localhost:15672/api/overview > /dev/null && echo "✅ RabbitMQ: OK" || echo "❌ RabbitMQ: FAILED"
