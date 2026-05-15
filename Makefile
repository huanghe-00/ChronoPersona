.PHONY: test lint format mock-demo eval install clean test-m1 test-m2 test-m3 test-m4 eval-full

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

# === Modular Testing (Schedule v2.0) ===
test-m1:
	pytest tests/test_lww_map.py tests/test_sliding_window.py tests/test_episodic.py tests/test_semantic.py -v --tb=short

test-m2:
	pytest tests/test_agent_core.py tests/test_emotion_engine.py tests/test_state_machine.py -v --tb=short

test-m3:
	pytest tests/test_a1_a3.py tests/test_a4_a5.py tests/test_a6_intent_graph.py -v --tb=short

test-m4:
	pytest tests/test_grid_world.py tests/test_embodied_adapter.py -v --tb=short

eval-full:
	python -m evaluation.runner --all

# === Cleanup ===
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .mypy_cache/
