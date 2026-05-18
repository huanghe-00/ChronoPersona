"""MVO (Minimum Viable Ontology) seed loader."""

from __future__ import annotations

from chronopersona.contracts.schemas.semantic import Concept, IntentPattern
from chronopersona.memory_system.l3_semantic.intent_graph import IntentGraph


class MVOSeedLoader:
    """Load MVO seeds into an IntentGraph."""

    DEFAULT_CONCEPTS: list[Concept] = [
        Concept("c_food", "食物", "abstract", None),
        Concept("c_cuisine", "菜系", "abstract", "c_food"),
        Concept("c_sichuan", "川菜", "food", "c_cuisine"),
        Concept("c_cantonese", "粤菜", "food", "c_cuisine"),
        Concept("c_emotion", "情绪", "abstract", None),
        Concept("c_anxiety", "焦虑", "emotion", "c_emotion"),
        Concept("c_joy", "喜悦", "emotion", "c_emotion"),
        Concept("c_person", "人物", "abstract", None),
        Concept("c_family", "家人", "relation", "c_person"),
    ]

    DEFAULT_PATTERNS: list[IntentPattern] = [
        IntentPattern("temporal_trace", ["后来", "之后", "然后", "接着"], ["TEMPORAL_NEXT", "MENTIONS"], 3),
        IntentPattern("causal_explore", ["为什么", "怎么回事", "原因"], ["CAUSED", "MENTIONS"], 3),
        IntentPattern("vertical_generalize", ["种类", "类型", "还有哪些"], ["IS_A"], 2),
        IntentPattern("vertical_specify", ["具体", "哪种", "什么样的"], ["IS_A"], 2),
        IntentPattern("parallel_compare", ["和", "相比", "哪个"], ["SIMILAR_TO"], 2),
        IntentPattern("empathize", ["难过", "开心", "生气"], ["MENTIONS"], 2),
    ]

    def __init__(self, graph: IntentGraph) -> None:
        self._graph = graph

    def load(self, branch_id: str = "main") -> None:
        """Idempotently load default MVO seeds into the graph."""
        existing = {c.id for c in self._graph.get_concepts(branch_id)}
        for concept in self.DEFAULT_CONCEPTS:
            if concept.id not in existing:
                self._graph.add_concept(Concept(
                    id=concept.id,
                    name=concept.name,
                    concept_type=concept.concept_type,
                    parent_id=concept.parent_id,
                    branch_id=branch_id,
                ))
