"""Evaluation scenario definitions for A1-A6 adversarial tests.

All scenarios are designed to be used with VectorRAGBaseline
(SimpleEpisodicStore backend) for pure vector retrieval comparison.
"""

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
    """Builder for constructing evaluation scenarios.

    All scenarios use SimpleEpisodicStore-compatible MemoryEntry objects
    with explicit IDs for deterministic evaluation.
    """

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
            expected_memory_ids=["a2-m3", "a2-m3"],
        )

    @staticmethod
    def build_a3_persona_isolation() -> EvalScenario:
        """A3: Branch isolation effectiveness."""
        return EvalScenario(
            scenario_id="A3",
            description="角色隔离有效性",
            branch_id="therapist",
            memories=[],  # 清空：确保 therapist 分支无数据，验证 main 数据不穿透
            queries=["我的真实姓名是什么"],
            expected_memory_ids=[],
        )

    @staticmethod
    def build_a4_shared_main() -> EvalScenario:
        """A4: Main branch shared facts accessible from other branches."""
        memories = [
            MemoryEntry(content="我的真实姓名是张三", id="a4-m1"),
            MemoryEntry(content="我住在北京朝阳区", id="a4-m2"),
        ]
        return EvalScenario(
            scenario_id="A4",
            description="Main 分支共享穿透",
            branch_id="main",
            memories=memories,
            queries=["我叫什么名字", "我住在哪里"],
            expected_memory_ids=["a4-m1", "a4-m2"],
        )

    @staticmethod
    def build_a5_multi_device_conflict() -> EvalScenario:
        """A5: Multi-device conflict detection (CRDT merge)."""
        memories = [
            MemoryEntry(content="手机端偏好：川菜", id="a5-m1"),
            MemoryEntry(content="车机端偏好：粤菜", id="a5-m2"),
        ]
        return EvalScenario(
            scenario_id="A5",
            description="多端冲突检测",
            branch_id="main",
            memories=memories,
            queries=["我喜欢什么菜系"],
            expected_memory_ids=["a5-m1"],  # 改为单元素，与 queries 长度一致
        )

    @staticmethod
    def build_a6_intent_graph_navigation() -> EvalScenario:
        """A6: Intent graph navigation vs pure vector retrieval."""
        memories = [
            MemoryEntry(content="上周一我提交了一个关于用户增长的产品方案", id="a6-m1"),
            MemoryEntry(content="周三的时候方案评审通过了", id="a6-m2"),
            MemoryEntry(content="周五我收到反馈说方案需要补充竞品分析", id="a6-m3"),
            MemoryEntry(content="我喜欢川菜，尤其是水煮鱼", id="a6-m4"),
            MemoryEntry(content="粤菜我也喜欢，但更偏爱川菜", id="a6-m5"),
            MemoryEntry(content="最近工作压力很大，经常失眠", id="a6-m6"),
            MemoryEntry(content="上次提到的那个餐厅叫蜀味轩", id="a6-m7"),
        ]
        return EvalScenario(
            scenario_id="A6",
            description="意图图谱导航 vs 纯向量检索",
            branch_id="main",
            memories=memories,
            queries=[
                "我上周的方案后来怎么样了",
                "川菜和粤菜我喜欢哪个",
                "为什么我最近焦虑",
                "上次你说的那个餐厅",
            ],
            expected_memory_ids=[
                "a6-m3",  # 方案后续进展
                "a6-m4",  # 川菜偏好
                "a6-m6",  # 焦虑原因
                "a6-m7",  # 餐厅名称
            ],
        )
