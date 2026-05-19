"""Checkpoint 3.1: 10-turn conversation stability test."""

import pytest

from chronopersona.agent_core import StateMachineAgentCore
from chronopersona.contracts.schemas import MemoryEntry
from chronopersona.contracts.schemas.semantic import Concept, IntentPattern, SemanticEdge
from chronopersona.memory_system.l2_episodic import SimpleEpisodicStore
from chronopersona.memory_system.l3_semantic import IntentGraph, IntentNavigator, MVOSeedLoader
from chronopersona.mocks import MockModelRouter


class TestCheckpoint31:
    """10-turn stability: L1/L2/L3 intact, Intent Graph recall works."""

    def test_ten_turn_stability(self) -> None:
        """Simulate 10 turns and verify memory layers remain consistent."""
        l2 = SimpleEpisodicStore()
        graph = IntentGraph()
        MVOSeedLoader(graph).load("main")

        core = StateMachineAgentCore(
            memory_store=l2,
            model_router=MockModelRouter(),
        )

        turns = [
            "你好，我是小明",
            "我喜欢川菜",
            "上周我们去的那家餐厅很不错",
            "后来我又去了一次",
            "你觉得川菜和粤菜哪个好",
            "我最近有点焦虑",
            "工作压力太大了",
            "记得提醒我买咖啡豆",
            "今天天气不错",
            "对了，我叫什么名字",
        ]

        for i, user_input in enumerate(turns):
            core.run_turn(user_input, branch_id="main")
            # Simulate async reflection: add memory node and MENTIONS edge
            mem_id = f"mem-{i}"
            l2.add(MemoryEntry(content=user_input), branch_id="main")
            graph.add_memory_node(mem_id, "main")
            for concept in graph.get_concepts("main"):
                if concept.name in user_input:
                    graph.add_edge(SemanticEdge(
                        id=f"e-{i}",
                        source_id=concept.id,
                        target_id=mem_id,
                        edge_type="MENTIONS",
                        branch_id="main",
                    ))

        # Verify L2 has memories
        ctx = l2.retrieve("川菜", branch_id="main")
        assert len(ctx.episodic_memories) >= 1

        # Verify L3 graph navigation works after 10 turns
        pattern = IntentPattern("retrieve", ["川菜"], ["MENTIONS"], 3)
        nav = IntentNavigator(graph, [pattern])
        results = nav.navigate("我喜欢川菜", "retrieve", "main")
        assert len(results) >= 1

    def test_branch_isolation_after_10_turns(self) -> None:
        """Memories remain isolated by branch after multiple turns."""
        l2 = SimpleEpisodicStore()
        core = StateMachineAgentCore(
            memory_store=l2,
            model_router=MockModelRouter(),
        )
        for i in range(10):
            core.run_turn(f"turn {i}", branch_id="branch-a")
        ctx = l2.retrieve("turn", branch_id="branch-b")
        assert len(ctx.episodic_memories) == 0
