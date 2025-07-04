# .github/ISSUE_TEMPLATE/feature_request.md
# ===================================

---
name: Feature request
about: Suggest an idea for this project
title: '[FEATURE] '
labels: enhancement
assignees: ''

---

**Is your feature request related to a problem? Please describe.**
A clear and concise description of what the problem is. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear and concise description of what you want to happen.

**Describe alternatives you've considered**
A clear and concise description of any alternative solutions or features you've considered.

**Additional context**
Add any other context or screenshots about the feature request here.

**Implementation suggestions**
If you have ideas about how this could be implemented, please share them.

# ===================================

# .github/pull_request_template.md
# ===================================

## Description

Brief description of changes made.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring (no functional changes)

## How Has This Been Tested?

- [ ] Unit tests
- [ ] Integration tests
- [ ] SITL tests
- [ ] Manual testing

Test environment:
- OS: 
- Python version:
- Backend:

## Checklist

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Any dependent changes have been merged and published

## Screenshots (if appropriate)

## Additional Notes

Any additional information, configuration, or data that might be necessary to reproduce the issue.

# ===================================

# Makefile
# ===================================

.PHONY: help install test lint format clean dev sitl docker docs

# Default target
help: ## Show this help message
	@echo "DroneSphere Development Commands"
	@echo "==============================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install development dependencies
	@scripts/setup_dev.sh

test: ## Run all tests
	@scripts/test.sh all

test-unit: ## Run unit tests only
	@scripts/test.sh unit

test-integration: ## Run integration tests
	@scripts/test.sh integration

test-sitl: ## Run SITL integration tests
	@scripts/test.sh sitl

test-coverage: ## Run tests with coverage
	@scripts/test.sh --coverage all

lint: ## Run linting checks
	@scripts/lint.sh

format: ## Auto-format code
	@scripts/lint.sh --fix

clean: ## Clean up build artifacts
	@echo "🧹 Cleaning up..."
	@rm -rf .pytest_cache/
	@rm -rf .coverage
	@rm -rf htmlcov/
	@rm -rf dist/
	@rm -rf build/
	@rm -rf *.egg-info/
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "✅ Cleanup complete"

dev: ## Start development environment
	@echo "🚀 Starting development environment..."
	@echo "Starting SITL in background..."
	@scripts/run_sitl.sh &
	@sleep 10
	@echo "Starting agent..."
	@python -m dronesphere.agent &
	@echo "Starting server..."
	@uvicorn dronesphere.server.api:app --port 8000 --reload

sitl: ## Start SITL environment only
	@scripts/run_sitl.sh

docker: ## Build Docker images
	@scripts/build.sh

docker-dev: ## Start development with Docker
	@docker-compose up

docker-prod: ## Start production with Docker
	@docker-compose -f docker-compose.prod.yml up -d

docs: ## Build and serve documentation
	@echo "📚 Building documentation..."
	@mkdocs serve

docs-build: ## Build documentation for production
	@mkdocs build

# Development shortcuts
run-agent: ## Run agent only
	@python -m dronesphere.agent

run-server: ## Run server only
	@uvicorn dronesphere.server.api:app --port 8000 --reload

run-tests-watch: ## Run tests in watch mode
	@ptw -- tests/unit/

# CI/CD helpers
ci-lint: ## Run CI linting
	@ruff check dronesphere/ tests/
	@black --check dronesphere/ tests/
	@isort --check-only dronesphere/ tests/
	@mypy dronesphere/

ci-test: ## Run CI tests
	@pytest tests/unit/ -v --cov=dronesphere --cov-report=xml

ci-build: ## Build for CI
	@docker build -f docker/Dockerfile.server -t dronesphere/server:test .
	@docker build -f docker/Dockerfile.agent -t dronesphere/agent:test .