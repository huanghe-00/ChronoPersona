"""MVCC versioning schemas for branch and entity-level snapshot management."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional


@dataclass
class Version:
    """MVCC version metadata for branch snapshots."""

    branch_id: str = ""
    version: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    vector_clock: Dict[str, int] = field(default_factory=dict)
    parent: Optional[str] = None
    content_hash: str = ""


@dataclass
class Snapshot:
    """Branch state snapshot used by checkout operations."""

    branch_id: str = ""
    version: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    state: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChangeSet:
    """Structured delta describing changes to be committed."""

    branch_id: str = ""
    operations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MergeResult:
    """Result of a branch merge operation."""

    source_branch: str = ""
    target_branch: str = ""
    merged_version: Optional[str] = None
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    auto_resolution_rate: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
