# Testing Guide for Assistant to the Regional Manager

## 🚀 Quick Start

### 1. Install Test Dependencies
```bash
make install
# or
pip install -r requirements-test.txt
```

### 2. Run All Tests
```bash
make test
# or
pytest
```

### 3. Run Tests with Coverage
```bash
make test-cov
# or
pytest --cov=backend --cov-report=term-missing --cov-report=html:htmlcov
```

## 📋 Available Test Commands

### Basic Testing
```bash
# Run all tests
make test

# Run unit tests only (fast)
make test-unit

# Run integration tests only
make test-integration

# Run tests with coverage report
make test-cov

# Run tests in parallel (faster)
make test-fast
```

### Advanced Testing
```bash
# Run specific test file
make test-file FILE=tests/test_api_endpoints.py

# Run tests matching a pattern
make test-pattern PATTERN=test_user_data

# Run tests with specific marker
make test-marker MARKER=unit

# Run tests with database (requires Docker)
make test-with-db

# Quick smoke test
make smoke-test
```

### Development Workflow
```bash
# Run tests in watch mode (auto-rerun on file changes)
make test-watch

# Run tests with verbose output and debugging
make test-debug

# Clean up test artifacts
make clean

# Format code
make format

# Run linting
make lint
```

## 🏗️ Test Structure

### Test Categories
- **Unit Tests**: Fast, isolated tests for individual functions
- **Integration Tests**: Tests that require external services (database, Redis)
- **API Tests**: End-to-end API endpoint testing
- **Slow Tests**: Tests that take longer to run (marked with `@pytest.mark.slow`)

### Test Markers
```python
@pytest.mark.unit          # Unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.slow         # Slow running tests
@pytest.mark.api          # API tests
@pytest.mark.auth         # Authentication tests
@pytest.mark.vector_store # Vector store tests
@pytest.mark.redis        # Redis tests
@pytest.mark.database     # Database tests
@pytest.mark.user_data    # User data deletion tests
```

## 🔧 Efficient Testing Workflows

### 1. Development Workflow
```bash
# 1. Start with unit tests (fast feedback)
make test-unit

# 2. Run specific test you're working on
make test-pattern PATTERN=test_function_name

# 3. Run with coverage to see what's missing
make test-cov

# 4. Run integration tests before committing
make test-integration
```

### 2. CI/CD Workflow
```bash
# 1. Clean environment
make clean

# 2. Install dependencies
make install

# 3. Run all tests with coverage
make test-cov

# 4. Run linting
make lint
```

### 3. Debugging Workflow
```bash
# 1. Run with verbose output
make test-debug

# 2. Run specific failing test
pytest tests/test_file.py::test_function -v -s

# 3. Run with database for integration issues
make test-with-db
```

## 📊 Coverage Reports

### Generate Coverage Report
```bash
make coverage-report
```

### View Coverage Report
```bash
# Open in browser
open htmlcov/index.html
```


## 🐛 Debugging Tests

### Common Issues

#### 1. Import Errors
```bash
# Add backend to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
```

#### 2. Database Connection Issues
```bash
# Start required services
docker-compose up postgres redis -d

# Run database tests
pytest -m database
```

#### 3. Redis Connection Issues
```bash
# Check Redis is running
docker-compose ps redis

# Run Redis tests
pytest -m redis
```

### Debugging Commands
```bash
# Run single test with full output
pytest tests/test_file.py::test_function -v -s --tb=long

# Run with pdb debugger
pytest tests/test_file.py::test_function -v -s --pdb

# Run with print statements visible
pytest tests/test_file.py::test_function -v -s -rP
```
