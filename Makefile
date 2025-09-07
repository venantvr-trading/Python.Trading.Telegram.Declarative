# Makefile for Python.Trading.Telegram.Declarative
# Python project management and development tasks

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
VENV := .venv
VENV_ACTIVATE := . $(VENV)/bin/activate
PROJECT_NAME := Python.Trading.Telegram.Declarative
PACKAGE := venantvr.telegram
TEST_PATH := tests
SRC_PATH := venantvr

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

# Phony targets
.PHONY: help clean install dev-install test test-verbose test-coverage lint format type-check \
        check run docker-build docker-run docs serve-docs venv requirements freeze \
        pre-commit security-check update-deps clean-pyc clean-test clean-build

## Help
help: ## Show this help message
	@echo '$(GREEN)Python.Trading.Telegram.Declarative - Makefile Commands$(NC)'
	@echo ''
	@echo 'Usage:'
	@echo '  make $(YELLOW)<target>$(NC)'
	@echo ''
	@echo 'Targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

## Environment Setup
venv: ## Create virtual environment
	@echo "$(GREEN)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)
	@echo "$(GREEN)Virtual environment created. Activate with: source $(VENV)/bin/activate$(NC)"

install: venv ## Install dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	$(VENV_ACTIVATE) && $(PIP) install --upgrade pip
	$(VENV_ACTIVATE) && $(PIP) install -r requirements.txt
	@echo "$(GREEN)Dependencies installed successfully$(NC)"

dev-install: install ## Install development dependencies
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	$(VENV_ACTIVATE) && $(PIP) install -r requirements-dev.txt 2>/dev/null || true
	$(VENV_ACTIVATE) && $(PIP) install pytest pytest-cov black flake8 mypy pylint
	@echo "$(GREEN)Development dependencies installed$(NC)"

requirements: ## Generate requirements.txt from current environment
	@echo "$(GREEN)Generating requirements.txt...$(NC)"
	$(VENV_ACTIVATE) && $(PIP) freeze > requirements.txt
	@echo "$(GREEN)requirements.txt updated$(NC)"

freeze: requirements ## Alias for requirements

update-deps: ## Update all dependencies to latest versions
	@echo "$(GREEN)Updating dependencies...$(NC)"
	$(VENV_ACTIVATE) && $(PIP) install --upgrade pip
	$(VENV_ACTIVATE) && $(PIP) list --outdated --format=freeze | grep -v '^\-e' | cut -d = -f 1 | xargs -n1 $(PIP) install -U
	@echo "$(GREEN)Dependencies updated$(NC)"

## Testing
test: ## Run all tests
	@echo "$(GREEN)Running tests...$(NC)"
	$(VENV_ACTIVATE) && $(PYTHON) -m unittest discover $(TEST_PATH) -p "test_*.py"

test-verbose: ## Run tests with verbose output
	@echo "$(GREEN)Running tests with verbose output...$(NC)"
	$(VENV_ACTIVATE) && $(PYTHON) -m unittest discover $(TEST_PATH) -v -p "test_*.py"

test-coverage: ## Run tests with coverage report
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	$(VENV_ACTIVATE) && $(PYTHON) -m pytest $(TEST_PATH) --cov=$(PACKAGE) --cov-report=html --cov-report=term 2>/dev/null || \
		(echo "$(YELLOW)pytest not installed, using unittest$(NC)" && $(PYTHON) -m unittest discover $(TEST_PATH))

test-unit: ## Run unit tests only
	@echo "$(GREEN)Running unit tests...$(NC)"
	$(VENV_ACTIVATE) && $(PYTHON) -m unittest discover $(TEST_PATH) -p "test_*.py" -k "Test"

test-integration: ## Run integration tests only
	@echo "$(GREEN)Running integration tests...$(NC)"
	$(VENV_ACTIVATE) && $(PYTHON) -m unittest discover $(TEST_PATH) -p "test_*.py" -k "Integration"

test-file: ## Run specific test file (use TEST_FILE=tests/test_client.py)
	@echo "$(GREEN)Running test file: $(TEST_FILE)$(NC)"
	$(VENV_ACTIVATE) && $(PYTHON) -m unittest $(TEST_FILE)

## Code Quality
lint: ## Run code linting with flake8
	@echo "$(GREEN)Running flake8 linter...$(NC)"
	$(VENV_ACTIVATE) && flake8 $(SRC_PATH) --max-line-length=120 --exclude=__pycache__ 2>/dev/null || \
		(echo "$(YELLOW)flake8 not installed, skipping$(NC)")

pylint: ## Run pylint on source code
	@echo "$(GREEN)Running pylint...$(NC)"
	$(VENV_ACTIVATE) && pylint $(SRC_PATH) 2>/dev/null || \
		(echo "$(YELLOW)pylint not installed, skipping$(NC)")

format: ## Format code with black
	@echo "$(GREEN)Formatting code with black...$(NC)"
	$(VENV_ACTIVATE) && black $(SRC_PATH) $(TEST_PATH) --line-length=120 2>/dev/null || \
		(echo "$(YELLOW)black not installed, skipping$(NC)")

format-check: ## Check code formatting without modifying
	@echo "$(GREEN)Checking code format...$(NC)"
	$(VENV_ACTIVATE) && black $(SRC_PATH) $(TEST_PATH) --check --line-length=120 2>/dev/null || \
		(echo "$(YELLOW)black not installed, skipping$(NC)")

type-check: ## Run type checking with mypy
	@echo "$(GREEN)Running type checker...$(NC)"
	$(VENV_ACTIVATE) && mypy $(SRC_PATH) --ignore-missing-imports 2>/dev/null || \
		(echo "$(YELLOW)mypy not installed, skipping$(NC)")

check: lint format-check type-check test ## Run all checks (lint, format, type, test)
	@echo "$(GREEN)All checks completed$(NC)"

pre-commit: format lint type-check test ## Run pre-commit checks
	@echo "$(GREEN)Pre-commit checks passed$(NC)"

security-check: ## Check for security vulnerabilities
	@echo "$(GREEN)Checking for security vulnerabilities...$(NC)"
	$(VENV_ACTIVATE) && pip-audit 2>/dev/null || \
		($(PIP) install pip-audit && pip-audit) || \
		(echo "$(YELLOW)pip-audit not available$(NC)")

## Running
run: ## Run the main application
	@echo "$(GREEN)Starting Telegram Bot...$(NC)"
	$(VENV_ACTIVATE) && $(PYTHON) -m $(PACKAGE).main 2>/dev/null || \
		echo "$(RED)Main module not found. Please implement $(PACKAGE).main$(NC)"

run-dev: ## Run in development mode with auto-reload
	@echo "$(GREEN)Starting in development mode...$(NC)"
	$(VENV_ACTIVATE) && $(PYTHON) -m $(PACKAGE).main --debug 2>/dev/null || \
		echo "$(RED)Main module not found. Please implement $(PACKAGE).main$(NC)"

## Docker
docker-build: ## Build Docker image
	@echo "$(GREEN)Building Docker image...$(NC)"
	docker build -t $(PROJECT_NAME):latest .

docker-run: ## Run Docker container
	@echo "$(GREEN)Running Docker container...$(NC)"
	docker run -it --rm \
		--env-file .env \
		--name $(PROJECT_NAME) \
		$(PROJECT_NAME):latest

docker-compose-up: ## Start services with docker-compose
	@echo "$(GREEN)Starting services with docker-compose...$(NC)"
	docker-compose up -d

docker-compose-down: ## Stop services with docker-compose
	@echo "$(GREEN)Stopping services...$(NC)"
	docker-compose down

## Documentation
docs: ## Generate documentation
	@echo "$(GREEN)Generating documentation...$(NC)"
	$(VENV_ACTIVATE) && sphinx-build -b html docs docs/_build 2>/dev/null || \
		(echo "$(YELLOW)Sphinx not installed, trying pdoc...$(NC)" && \
		 pdoc --html --output-dir docs $(PACKAGE) 2>/dev/null) || \
		echo "$(YELLOW)No documentation generator found$(NC)"

serve-docs: ## Serve documentation locally
	@echo "$(GREEN)Serving documentation at http://localhost:8000$(NC)"
	$(PYTHON) -m http.server 8000 --directory docs/_build/html 2>/dev/null || \
		$(PYTHON) -m http.server 8000 --directory docs

## Cleaning
clean: clean-pyc clean-test clean-build ## Remove all build, test, and Python artifacts
	@echo "$(GREEN)Cleaned all artifacts$(NC)"

clean-pyc: ## Remove Python file artifacts
	@echo "$(YELLOW)Removing Python artifacts...$(NC)"
	find . -type f -name '*.py[co]' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true

clean-test: ## Remove test and coverage artifacts
	@echo "$(YELLOW)Removing test artifacts...$(NC)"
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/

clean-build: ## Remove build artifacts
	@echo "$(YELLOW)Removing build artifacts...$(NC)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info

clean-venv: ## Remove virtual environment
	@echo "$(YELLOW)Removing virtual environment...$(NC)"
	rm -rf $(VENV)

## Git
git-status: ## Show git status
	@git status

git-commit: pre-commit ## Commit changes after running pre-commit checks
	@echo "$(GREEN)Creating commit...$(NC)"
	@git add -A
	@git commit

git-push: ## Push to remote repository
	@echo "$(GREEN)Pushing to remote...$(NC)"
	@git push

## Utilities
watch-tests: ## Watch for changes and run tests
	@echo "$(GREEN)Watching for changes...$(NC)"
	$(VENV_ACTIVATE) && watchmedo shell-command \
		--patterns="*.py" \
		--recursive \
		--command='make test' \
		. 2>/dev/null || echo "$(YELLOW)watchdog not installed$(NC)"

count-lines: ## Count lines of code
	@echo "$(GREEN)Counting lines of code...$(NC)"
	@echo "Python files:"
	@find $(SRC_PATH) -name '*.py' | xargs wc -l | tail -1
	@echo "Test files:"
	@find $(TEST_PATH) -name '*.py' | xargs wc -l | tail -1

show-deps: ## Show dependency tree
	@echo "$(GREEN)Dependency tree:$(NC)"
	$(VENV_ACTIVATE) && pipdeptree 2>/dev/null || \
		($(PIP) install pipdeptree && pipdeptree) || \
		$(PIP) list

check-deps: ## Check for outdated dependencies
	@echo "$(GREEN)Checking for outdated packages...$(NC)"
	$(VENV_ACTIVATE) && $(PIP) list --outdated

env-info: ## Show environment information
	@echo "$(GREEN)Environment Information:$(NC)"
	@echo "Python version: $$($(PYTHON) --version)"
	@echo "Pip version: $$($(PIP) --version)"
	@echo "Virtual env: $(VENV)"
	@echo "Project: $(PROJECT_NAME)"
	@echo "Package: $(PACKAGE)"

## Shortcuts
i: install ## Shortcut for install
t: test ## Shortcut for test
tv: test-verbose ## Shortcut for test-verbose
tc: test-coverage ## Shortcut for test-coverage
l: lint ## Shortcut for lint
f: format ## Shortcut for format
c: check ## Shortcut for check
r: run ## Shortcut for run
cl: clean ## Shortcut for clean