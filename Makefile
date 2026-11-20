.PHONY: all setup test test-a test-b benchmark-a benchmark-b profile-b download-data clean

PYTHON = PYTHONPATH=. .venv/bin/python
PYTEST = PYTHONPATH=. .venv/bin/pytest

all: test benchmark-a benchmark-b

setup:
	@echo "=== Setting up virtual environment ==="
	uv venv .venv
	. .venv/bin/activate && uv pip install google-genai pandas numpy pydantic pytest requests python-dotenv scikit-learn rapidfuzz pyarrow
	@echo "=== Setup complete ==="

test: test-a test-b

test-a:
	@echo "=== Running Project A tests ==="
	$(PYTEST) project_a/tests/ -v --tb=short

test-b:
	@echo "=== Running Project B tests ==="
	$(PYTEST) project_b/tests/ -v --tb=short

benchmark-a:
	@echo "=== Running Project A benchmarks ==="
	$(PYTHON) -m project_a.benchmark

benchmark-b:
	@echo "=== Running Project B benchmarks ==="
	$(PYTHON) -m project_b.benchmark

profile-b:
	@echo "=== Profiling NYC 311 data ==="
	$(PYTHON) -m project_b.profiler

download-data:
	@echo "=== Downloading NYC 311 2023 data ==="
	$(PYTHON) -m project_b.data_loader

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache
