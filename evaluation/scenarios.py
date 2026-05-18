"""Evaluation scenario definitions for A1-A3 adversarial tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from chronopersona.contracts.schemas import MemoryEntry


@dataclass
class EvalScenario:
    """Single evaluation scenario with ground truth."""

    scenario_id: str
    description: str
    branch_id: str
    memories: List[MemoryEntry]
    queries: List[str]
    expected_memory_ids: List[str]


class ScenarioBuilder:
    """Builder for constructing evaluation scenarios."""

    @staticmethod
    def build_a1_memory_recall() -> EvalScenario:
        """A1: Cross-session factual retrieval."""
        memories = [
            MemoryEntry(content="我的手机号是13800138000", id="a1-m1"),
            MemoryEntry(content="我喜欢在周末去爬山", id="a1-m2"),
            MemoryEntry(content="我的宠物狗叫豆豆", id="a1-m3"),
            MemoryEntry(content="我在腾讯工作，职位是后端工程师", id="a1-m4"),
        ]
        return EvalScenario(
            scenario_id="A1",
            description="跨 session 事实检索",
            branch_id="main",
            memories=memories,
            queries=["我的手机号是多少", "我的狗叫什么名字", "我在哪里工作"],
            expected_memory_ids=["a1-m1", "a1-m3", "a1-m4"],
        )

    @staticmethod
    def build_a2_cross_session() -> EvalScenario:
        """A2: Temporal reasoning across sessions."""
        memories = [
            MemoryEntry(content="上周一我提到要提交一个方案", id="a2-m1"),
            MemoryEntry(content="周三的时候方案已经写完了", id="a2-m2"),
            MemoryEntry(content="周五我收到反馈说方案通过了", id="a2-m3"),
        ]
        return EvalScenario(
            scenario_id="A2",
            description="时间线推理",
            branch_id="main",
            memories=memories,
            queries=["我上周的方案后来怎么样了", "那个方案通过了吗"],
            expected_memory_ids=["a2-m3"],
        )

    @staticmethod
    def build_a3_persona_isolation() -> EvalScenario:
        """A3: Branch isolation effectiveness."""
        memories = [
            MemoryEntry(content="来访者表示最近压力很大", id="a3-t1"),
        ]
        return EvalScenario(
            scenario_id="A3",
            description="角色隔离有效性",
            branch_id="therapist",
            memories=memories,
            queries=["我的真实姓名是什么"],
            expected_memory_ids=[],
        )
