# DroneSphere Makefile - Using UV Package Manager
# ================================================

# Variables
PYTHON := python
UV := uv
PROJECT_NAME := dronesphere
SRC_DIR := src
TEST_DIR := tests
SCRIPTS_DIR := scripts

# Docker compose files
DOCKER_COMPOSE := docker-compose -f deploy/docker/docker-compose.yaml
DOCKER_COMPOSE_TEST := docker-compose -f deploy/docker/docker-compose.test.yaml

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

# Phony targets
.PHONY: help install install-dev setup clean format lint type-check test \
        run run-dev docker-up docker-down docker-logs db-migrate db-reset \
        quality docs pi-deploy pi-logs

# Help target
help: ## Show this help message
	@echo "$(GREEN)DroneSphere Development Commands$(NC)"
	@echo "=================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Quick Start:$(NC)"
	@echo "  make setup       # Complete setup"
	@echo "  make docker-up   # Start services"
	@echo "  make run-dev     # Run development server"

# Installation targets
install: ## Install production dependencies
	@echo "$(GREEN)Installing production dependencies with UV...$(NC)"
	$(UV) pip install -e .

install-dev: ## Install all dependencies including dev
	@echo "$(GREEN)Installing all dependencies with UV...$(NC)"
	$(UV) pip install -e ".[dev]"

setup: ## Complete development setup
	@echo "$(GREEN)Setting up DroneSphere development environment...$(NC)"
	@echo "1. Creating virtual environment..."
	$(UV) venv
	@echo ""
	@echo "2. Installing dependencies..."
	$(UV) pip install -e ".[dev]"
	@echo ""
	@echo "3. Installing pre-commit hooks..."
	pre-commit install
	@echo ""
	@echo "4. Setting up environment file..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file"; fi
	@echo ""
	@echo "$(GREEN)✅ Setup complete! Activate with: source .venv/bin/activate$(NC)"

# Code quality targets
format: ## Format code with black and isort
	@echo "$(GREEN)Formatting code...$(NC)"
	black $(SRC_DIR) $(TEST_DIR) $(SCRIPTS_DIR)
	isort $(SRC_DIR) $(TEST_DIR) $(SCRIPTS_DIR)

lint: ## Run linting with flake8
	@echo "$(GREEN)Running linters...$(NC)"
	flake8 $(SRC_DIR) $(TEST_DIR)

type-check: ## Run type checking with mypy
	@echo "$(GREEN)Running type checks...$(NC)"
	mypy $(SRC_DIR)

quality: format lint type-check ## Run all code quality checks

# Testing targets
test: ## Run all tests
	@echo "$(GREEN)Running all tests...$(NC)"
	pytest $(TEST_DIR) -v

test-unit: ## Run unit tests only
	@echo "$(GREEN)Running unit tests...$(NC)"
	pytest $(TEST_DIR)/unit -v

test-integration: ## Run integration tests only
	@echo "$(GREEN)Running integration tests...$(NC)"
	pytest $(TEST_DIR)/integration -v

test-cov: ## Run tests with coverage report
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode
	@echo "$(GREEN)Running tests in watch mode...$(NC)"
	ptw $(TEST_DIR)

test-domain: ## Test domain models
	@echo "$(GREEN)Testing domain models...$(NC)"
	$(PYTHON) $(SCRIPTS_DIR)/test_domain_models.py

# Running targets
run: ## Run the application
	@echo "$(GREEN)Starting DroneSphere server...$(NC)"
	uvicorn src.adapters.input.api.main:app --host 0.0.0.0 --port 8000

run-dev: ## Run with hot reload
	@echo "$(GREEN)Starting DroneSphere server (dev mode)...$(NC)"
	uvicorn src.adapters.input.api.main:app --host 0.0.0.0 --port 8000 --reload

shell: ## Open Python shell with app context
	@echo "$(GREEN)Opening Python shell...$(NC)"
	ipython

# Docker targets
docker-up: ## Start all Docker services
	@echo "$(GREEN)Starting Docker services...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)Services started! Checking status...$(NC)"
	@sleep 5
	$(DOCKER_COMPOSE) ps

docker-down: ## Stop all Docker services
	@echo "$(YELLOW)Stopping Docker services...$(NC)"
	$(DOCKER_COMPOSE) down

docker-logs: ## View Docker service logs
	$(DOCKER_COMPOSE) logs -f

docker-ps: ## List Docker services
	$(DOCKER_COMPOSE) ps

docker-clean: ## Remove all containers and volumes
	@echo "$(RED)Removing all containers and volumes...$(NC)"
	$(DOCKER_COMPOSE) down -v
	docker system prune -f

# Database targets
db-migrate: ## Run database migrations
	@echo "$(GREEN)Running database migrations...$(NC)"
	alembic upgrade head

db-rollback: ## Rollback last migration
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	alembic downgrade -1

db-reset: ## Reset database
	@echo "$(RED)Resetting database...$(NC)"
	$(DOCKER_COMPOSE) down postgres
	$(DOCKER_COMPOSE) up -d postgres
	@sleep 5
	alembic upgrade head
	@echo "$(GREEN)Database reset complete!$(NC)"

db-shell: ## Open database shell
	@echo "$(GREEN)Opening PostgreSQL shell...$(NC)"
	docker exec -it dronesphere-postgres psql -U dronesphere -d dronesphere

# Documentation targets
docs: ## Generate documentation
	@echo "$(GREEN)Generating documentation...$(NC)"
	mkdocs build

docs-serve: ## Serve documentation locally
	@echo "$(GREEN)Serving documentation at http://localhost:8001...$(NC)"
	mkdocs serve

# Raspberry Pi targets
pi-setup: ## Setup Raspberry Pi environment
	@echo "$(GREEN)Setting up Raspberry Pi environment...$(NC)"
	cd drone_controller && $(PYTHON) -m venv venv
	cd drone_controller && ./venv/bin/pip install -r requirements.txt

pi-deploy: ## Deploy to Raspberry Pi
	@echo "$(GREEN)Deploying to Raspberry Pi...$(NC)"
	@if [ -z "$(PI_HOST)" ]; then echo "$(RED)Error: PI_HOST not set$(NC)"; exit 1; fi
	rsync -av --exclude='.venv' --exclude='__pycache__' \
		drone_controller/ $(PI_USER)@$(PI_HOST):$(PI_PATH)/drone_controller/
	ssh $(PI_USER)@$(PI_HOST) "cd $(PI_PATH)/drone_controller && source venv/bin/activate && pip install -r requirements.txt"
	@echo "$(GREEN)Deployment complete!$(NC)"

pi-logs: ## View Raspberry Pi logs
	@if [ -z "$(PI_HOST)" ]; then echo "$(RED)Error: PI_HOST not set$(NC)"; exit 1; fi
	ssh $(PI_USER)@$(PI_HOST) "cd $(PI_PATH)/drone_controller && tail -f drone_controller.log"

pi-restart: ## Restart Raspberry Pi service
	@if [ -z "$(PI_HOST)" ]; then echo "$(RED)Error: PI_HOST not set$(NC)"; exit 1; fi
	ssh $(PI_USER)@$(PI_HOST) "sudo systemctl restart dronesphere-controller"

# Utility targets
clean: ## Clean build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Clean complete!$(NC)"

clean-all: clean ## Clean everything including venv
	@echo "$(RED)Removing virtual environment...$(NC)"
	rm -rf .venv
	rm -rf venv
	@echo "$(GREEN)All clean!$(NC)"

# Environment targets
env-show: ## Show current environment variables
	@echo "$(GREEN)Current environment:$(NC)"
	@env | grep -E '^(APP_|API_|DATABASE_|REDIS_|RABBITMQ_|DRONE_)' | sort

env-check: ## Check environment setup
	@echo "$(GREEN)Checking environment...$(NC)"
	$(PYTHON) $(SCRIPTS_DIR)/test_environment.py

# Development shortcuts
dev: docker-up run-dev ## Start everything for development

stop: docker-down ## Stop everything

restart: docker-down docker-up ## Restart all services

# Git shortcuts
commit: quality ## Run quality checks before commit
	@echo "$(GREEN)Quality checks passed! Ready to commit.$(NC)"

# UV specific commands
uv-sync: ## Sync dependencies with UV
	@echo "$(GREEN)Syncing dependencies...$(NC)"
	$(UV) pip sync

uv-upgrade: ## Upgrade all dependencies
	@echo "$(GREEN)Upgrading dependencies...$(NC)"
	$(UV) pip install --upgrade -e ".[dev]"

uv-cache-clean: ## Clean UV cache
	@echo "$(YELLOW)Cleaning UV cache...$(NC)"
	$(UV) cache clean

# Version and info
version: ## Show version information
	@echo "$(GREEN)DroneSphere Version Information$(NC)"
	@echo "================================"
	@echo "Project: $(PROJECT_NAME)"
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "UV: $(shell $(UV) --version)"
	@echo "Current commit: $(shell git rev-parse --short HEAD)"
	@echo "Current branch: $(shell git branch --show-current)"

.PHONY: all $(MAKECMDGOALS)