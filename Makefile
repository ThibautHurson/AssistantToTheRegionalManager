# Makefile for Assistant to the Regional Manager
# Testing and development commands

.PHONY: help install test test-unit test-integration test-cov test-fast test-watch clean lint format

# Default target
help:
	@echo "Available commands:"
	@echo "  install        - Install test dependencies"
	@echo "  test           - Run all tests"
	@echo "  test-unit      - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  test-cov       - Run tests with coverage report"
	@echo "  test-fast      - Run tests in parallel (faster)"
	@echo "  test-watch     - Run tests in watch mode (requires pytest-watch)"
	@echo "  test-debug     - Run tests with verbose output and debugging"
	@echo "  clean          - Clean up test artifacts"
	@echo "  lint           - Run linting checks"
	@echo "  format         - Format code with black"

# Install test dependencies
install:
	pip install -r requirements-test.txt

# Run all tests
test:
	pytest

# Run unit tests only
test-unit:
	pytest -m "not integration and not slow"

# Run integration tests only
test-integration:
	pytest -m "integration or slow"

# Run tests with coverage
test-cov:
	pytest --cov=backend --cov-report=term-missing --cov-report=html:htmlcov

# Run tests in parallel (faster)
test-fast:
	pytest -n auto

# Run tests in watch mode (requires pytest-watch)
test-watch:
	pytest-watch -- -v

# Run tests with verbose output and debugging
test-debug:
	pytest -v -s --tb=long

# Clean up test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf *.pyc
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete

# Run linting checks
lint:
	flake8 backend/ tests/
	pylint backend/ tests/ --rcfile=.pylintrc

# Format code
format:
	black backend/ tests/
	isort backend/ tests/

# Run specific test file
test-file:
	@echo "Usage: make test-file FILE=path/to/test_file.py"
	@if [ -z "$(FILE)" ]; then echo "Please specify FILE parameter"; exit 1; fi
	pytest $(FILE) -v

# Run tests matching a pattern
test-pattern:
	@echo "Usage: make test-pattern PATTERN=test_name"
	@if [ -z "$(PATTERN)" ]; then echo "Please specify PATTERN parameter"; exit 1; fi
	pytest -k "$(PATTERN)" -v

# Run tests with specific marker
test-marker:
	@echo "Usage: make test-marker MARKER=unit"
	@if [ -z "$(MARKER)" ]; then echo "Please specify MARKER parameter"; exit 1; fi
	pytest -m "$(MARKER)" -v

# Generate test coverage report
coverage-report:
	pytest --cov=backend --cov-report=html:htmlcov --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

# Run tests with database (requires Docker)
test-with-db:
	docker-compose up postgres redis -d
	sleep 5  # Wait for services to start
	pytest -m "database or integration"
	docker-compose down

# Quick smoke test
smoke-test:
	pytest tests/test_api_endpoints.py::test_health_check -v 