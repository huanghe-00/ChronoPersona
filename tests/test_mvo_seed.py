"""Tests for MVO seed loader."""

import os
import tempfile

import pytest

from chronopersona.memory_system.l3_semantic.intent_graph import IntentGraph
from chronopersona.memory_system.l3_semantic.mvo_seed_loader import MVOSeedLoader


class TestMVOSeedLoader:
    """Tests for MVO seed loading."""

    def test_load_populates_concepts(self) -> None:
        """Loading seeds populates default concepts."""
        graph = IntentGraph()
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "main.yaml"), "w") as f:
                f.write(
                    "concepts:\n"
                    "  - id: c1\n"
                    "    name: 川菜\n"
                    "    concept_type: food\n"
                    "    parent_id: null\n"
                    "    branch_id: main\n"
                )
            loader = MVOSeedLoader(graph, config_dir=tmp)
            result = loader.load("main", "main")
            assert result["concepts"] == 1
            assert len(graph.get_concepts("main")) == 1

    def test_load_is_idempotent(self) -> None:
        """Repeated loading does not duplicate concepts."""
        graph = IntentGraph()
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "main.yaml"), "w") as f:
                f.write(
                    "concepts:\n"
                    "  - id: c1\n"
                    "    name: 川菜\n"
                    "    concept_type: food\n"
                    "    parent_id: null\n"
                    "    branch_id: main\n"
                )
            loader = MVOSeedLoader(graph, config_dir=tmp)
            loader.load("main", "main")
            loader.load("main", "main")
            assert len(graph.get_concepts("main")) == 1

    def test_load_branch_isolation(self) -> None:
        """Seeds are loaded into specified branch only."""
        graph = IntentGraph()
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "b1.yaml"), "w") as f:
                f.write(
                    "concepts:\n"
                    "  - id: c1\n"
                    "    name: 川菜\n"
                    "    concept_type: food\n"
                    "    parent_id: null\n"
                    "    branch_id: b1\n"
                )
            loader = MVOSeedLoader(graph, config_dir=tmp)
            loader.load("b1", "b1")
            assert len(graph.get_concepts("b1")) == 1
            assert len(graph.get_concepts("main")) == 0

    def test_load_missing_domain_returns_zero(self) -> None:
        """Missing domain file returns zero counts."""
        graph = IntentGraph()
        with tempfile.TemporaryDirectory() as tmp:
            loader = MVOSeedLoader(graph, config_dir=tmp)
            result = loader.load("nonexistent", "main")
            assert result["concepts"] == 0
            assert result["patterns"] == 0

    def test_empty_args_raises_valueerror(self) -> None:
        """Empty domain or branch_id raises ValueError."""
        graph = IntentGraph()
        with tempfile.TemporaryDirectory() as tmp:
            loader = MVOSeedLoader(graph, config_dir=tmp)
            with pytest.raises(ValueError):
                loader.load("", "main")
            with pytest.raises(ValueError):
                loader.load("main", "")
