.PHONY: test lint format mock-demo eval install clean

# === Environment ===
install:
	pip install -r requirements.txt

# === Testing ===
test:
	pytest tests/ -v --tb=short

test-cov:
	pytest tests/ -v --cov=chronopersona --cov-report=term-missing

# === Code Quality ===
lint:
	ruff check .
	mypy chronopersona/

format:
	ruff check . --fix
	black chronopersona/ tests/

# === Demo ===
mock-demo:
	python demo_memory.py

# === Evaluation ===
eval:
	python -m evaluation.run_eval

# === Cleanup ===
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .mypy_cache/