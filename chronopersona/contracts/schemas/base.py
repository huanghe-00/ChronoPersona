from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from chronopersona.contracts.schemas.version import Snapshot, Version  # 统一从 version 模块引用


@dataclass
class MemoryEntry:
    """A single memory entry stored in the system.

    Attributes:
        id: Unique identifier.
        content: The memory content.
        memory_type: Either 'episodic' or 'semantic'.
        branch_id: The branch this memory belongs to.
        session_id: Optional session identifier.
        turn_id: Optional turn number within a session.
        entities: List of entity identifiers mentioned.
        emotion_tags: List of emotion tags associated with the memory.
        created_at: ISO-8601 timestamp of creation.
        metadata: Additional unstructured metadata.
    """

    id: str = ""
    content: str = ""
    memory_type: str = "episodic"
    branch_id: str = ""
    session_id: Optional[str] = None
    turn_id: Optional[int] = None
    entities: List[str] = field(default_factory=list)
    emotion_tags: List[str] = field(default_factory=list)
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Fact:
    """A structured fact associated with an entity.

    Attributes:
        entity_id: The entity this fact describes.
        attribute: The attribute name.
        value: The attribute value.
        confidence: Confidence score in [0.0, 1.0].
        branch_id: The branch this fact belongs to.
        created_at: ISO-8601 timestamp of creation.
    """

    entity_id: str = ""
    attribute: str = ""
    value: str = ""
    confidence: float = 1.0
    branch_id: str = ""
    created_at: str = ""


@dataclass
class RetrievedContext:
    """Assembled context returned by a memory retrieval operation.

    Attributes:
        working_memories: L1 working memory entries.
        episodic_memories: L2 episodic memory entries.
        semantic_facts: L3 semantic facts.
        insights: Active insights from the reflection engine.
        navigation_path: Steps taken during intent graph navigation.
        total_tokens: Estimated token count of the assembled context.
    """

    working_memories: List[MemoryEntry] = field(default_factory=list)
    episodic_memories: List[MemoryEntry] = field(default_factory=list)
    semantic_facts: List[Fact] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    navigation_path: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
