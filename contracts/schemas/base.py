"""Base data schemas for ChronoPersona memory system.

Defines core dataclasses used across all memory layers.
"""

import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class MemoryEntry:
    """Core memory entry used across L1/L2/L3 layers.

    Extended with Engram Schema fields for v0.7.0:
    - abstracted_fact: Reflection Agent async output
    - affective_valence: T0 emotion engine mapping
    - source_turn_index: original turn position in session
    """

    content: str
    memory_type: str = "episodic"
    branch_id: str = "main"
    session_id: Optional[str] = None
    turn_id: Optional[int] = None
    entities: List[str] = field(default_factory=list)
    emotion_tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    importance: float = 0.5
    access_count: int = 0
    ttl_hours: Optional[float] = None
    entropy_gain: Optional[float] = None
    last_accessed: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # v0.7.0 Engram Schema extensions
    abstracted_fact: Optional[str] = None
    affective_valence: Optional[float] = None
    source_turn_index: Optional[int] = None
    admission_score: Optional[float] = None

    # v1.1.0 Provenance chain extensions (requirements.md 12.1.1)
    source_memory_ids: List[str] = field(default_factory=list)
    extraction_model: Optional[str] = None
    extraction_confidence: Optional[float] = None

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
