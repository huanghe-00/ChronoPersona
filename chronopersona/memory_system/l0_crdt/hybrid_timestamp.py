"""Hybrid Logical Clock (HLC) implementation for LWW-CRDT."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, order=False)
class HybridTimestamp:
    """Hybrid timestamp with physical time (ns) and logical counter.

    Total order: compare physical first, then logical.
    """

    physical: int
    logical: int = 0

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, HybridTimestamp):
            return NotImplemented
        if self.physical != other.physical:
            return self.physical < other.physical
        return self.logical < other.logical

    def __le__(self, other: Any) -> bool:
        if not isinstance(other, HybridTimestamp):
            return NotImplemented
        return self == other or self < other

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, HybridTimestamp):
            return NotImplemented
        return not self <= other

    def __ge__(self, other: Any) -> bool:
        if not isinstance(other, HybridTimestamp):
            return NotImplemented
        return not self < other

    @classmethod
    def now(cls, logical: int = 0) -> HybridTimestamp:
        """Create a timestamp from current monotonic physical time."""
        return cls(physical=time.time_ns(), logical=logical)
