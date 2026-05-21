"""Tier 1 rule-based edge builder (MENTIONS, TEMPORAL_NEXT, CAUSED, etc.)."""

import re
from typing import List

from loguru import logger

from chronopersona.contracts.interfaces import IEdgeBuilder
from chronopersona.contracts.schemas.semantic import SemanticEdge


class SimpleEdgeBuilder(IEdgeBuilder):
    """Tier 1: Hard-rule edge builder. No LLM calls."""

    CAUSED_TEMPLATES = [
        r"因为(.+?)，所以(.+?)",
        r"(.+?)导致(.+?)",
        r"(.+?)使得(.+?)",
        r"(.+?)因此(.+?)",
        r"(.+?)引起了(.+?)",
    ]

    CONTRADICT_PATTERNS = [
        ("喜欢", "讨厌"),
        ("喜欢", "恨"),
        ("想", "不想"),
        ("是", "不是"),
    ]

    def supported_types(self) -> List[str]:
        return ["MENTIONS", "TEMPORAL_NEXT", "CAUSED", "CORRELATED", "CONTRADICTS"]

    def build_edges(
        self,
        turn_id: str,
        session_id: str,
        branch_id: str,
        content: str,
        entities: List[str],
        prev_turn_id: str | None = None,
    ) -> List[SemanticEdge]:
        if not branch_id or not turn_id:
            raise ValueError("branch_id and turn_id must not be empty")

        edges: List[SemanticEdge] = []

        # 1. MENTIONS: every entity mentioned in this turn
        for entity_id in entities:
            edges.append(
                SemanticEdge(
                    id=f"{turn_id}_mentions_{entity_id}",
                    source_id=turn_id,
                    target_id=entity_id,
                    edge_type="MENTIONS",
                    branch_id=branch_id,
                    weight=0.9,
                )
            )

        # 2. TEMPORAL_NEXT: link to previous turn in same session
        if prev_turn_id:
            edges.append(
                SemanticEdge(
                    id=f"{prev_turn_id}_next_{turn_id}",
                    source_id=prev_turn_id,
                    target_id=turn_id,
                    edge_type="TEMPORAL_NEXT",
                    branch_id=branch_id,
                    weight=1.0,
                )
            )

        # 3. CAUSED / CORRELATED: template matching
        caused = self._extract_caused(content, turn_id, branch_id)
        edges.extend(caused)

        # 4. CONTRADICTS: simple antonym detection
        contradictions = self._extract_contradicts(content, turn_id, branch_id, entities)
        edges.extend(contradictions)

        logger.info(
            "SimpleEdgeBuilder: built {} edges for turn {} (branch {})",
            len(edges), turn_id, branch_id
        )
        return edges

    def _extract_caused(
        self, content: str, turn_id: str, branch_id: str
    ) -> List[SemanticEdge]:
        edges: List[SemanticEdge] = []
        for pattern in self.CAUSED_TEMPLATES:
            for match in re.finditer(pattern, content):
                cause = match.group(1).strip()[:50]
                effect = match.group(2).strip()[:50]
                edges.append(
                    SemanticEdge(
                        id=f"{turn_id}_caused_{cause}_{effect}",
                        source_id=cause,
                        target_id=effect,
                        edge_type="CAUSED",
                        branch_id=branch_id,
                        weight=0.85,
                        metadata={"mva_only": True, "template": pattern},
                    )
                )
        return edges

    def _extract_contradicts(
        self, content: str, turn_id: str, branch_id: str, entities: List[str]
    ) -> List[SemanticEdge]:
        edges: List[SemanticEdge] = []
        for pos, neg in self.CONTRADICT_PATTERNS:
            if pos in content and neg in content:
                # Simple heuristic: link turn to a synthetic contradict marker
                edges.append(
                    SemanticEdge(
                        id=f"{turn_id}_contradict",
                        source_id=turn_id,
                        target_id=f"contradict_{pos}_{neg}",
                        edge_type="CONTRADICTS",
                        branch_id=branch_id,
                        weight=0.8,
                    )
                )
        return edges
