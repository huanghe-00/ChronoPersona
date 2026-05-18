.PHONY: test lint format mock-demo eval install clean test-w1 test-w2 test-w3 test-w4 test-w5 test-w6 test-w7 eval-full

PYTHON := python3

# === Environment ===
install:
	pip install -r requirements.txt

# === Testing ===
test:
	$(PYTHON) -m pytest tests/ -v --tb=short

test-cov:
	$(PYTHON) -m pytest tests/ -v --cov=chronopersona --cov-report=term-missing

# === Code Quality ===
lint:
	ruff check .
	mypy chronopersona/

format:
	ruff check . --fix
	black chronopersona/ tests/

# === Demo ===
mock-demo:
	$(PYTHON) demo_memory.py

# === Evaluation ===
eval:
	$(PYTHON) -m evaluation.run_eval

# === Phase-aligned Testing (Schedule v1.0) ===
test-w1:
	$(PYTHON) -m pytest tests/test_mock_pipeline.py -v --tb=short

test-w2:
	$(PYTHON) -m pytest tests/test_l0_sync_layer.py tests/test_l2_episodic.py tests/test_agent_core_state_machine.py tests/test_l1_working_memory.py tests/test_l0_l2_integration.py -v --tb=short

test-w3:
	$(PYTHON) -m pytest tests/test_semantic.py tests/test_intent_graph.py tests/test_intent_navigator.py tests/test_mvo_seed.py tests/test_a6_intent_graph.py tests/test_checkpoint_3_1.py -v --tb=short

test-w4:
	$(PYTHON) -m pytest tests/test_insight.py tests/test_caused_tier2.py -v --tb=short

test-w5:
	$(PYTHON) -m pytest tests/test_agent_core.py tests/test_emotion_engine.py tests/test_state_machine.py -v --tb=short

test-w6:
	$(PYTHON) -m pytest tests/test_a1_a3.py tests/test_a4_a5.py tests/test_a6_intent_graph.py tests/test_eval_pipeline.py -v --tb=short

test-w7:
	$(PYTHON) -m pytest tests/test_grid_world.py tests/test_embodied_adapter.py tests/test_action_bridge.py -v --tb=short

eval-full:
	$(PYTHON) -m evaluation.run_eval --all

# === Cleanup ===
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .pytest_cache/ .mypy_cache/
