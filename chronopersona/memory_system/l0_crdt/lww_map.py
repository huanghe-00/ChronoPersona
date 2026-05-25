"""Last-Write-Wins Map with HLC-based conflict detection."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

from chronopersona.memory_system.l0_crdt.hybrid_timestamp import HybridTimestamp

MAX_CLOCK_SKEW_NS: int = 500_000_000
MAX_CONTRADICT_KEYS: int = 10  # Soft limit: alarm when total skew-conflicted keys exceed this


@dataclass
class LWWEntry:
    """Internal entry holding value, timestamp, and originating device."""

    value: Any
    timestamp: HybridTimestamp
    device_id: str


@dataclass
class ClockSkewConflict:
    """Represents a suspected clock skew between two entries for the same key."""

    key: str
    local_entry: LWWEntry
    remote_entry: LWWEntry


class LWWMap:
    """Last-Write-Wins map with add-wins semantics and clock-skew detection."""

    def __init__(self, device_id: str) -> None:
        self.device_id: str = device_id
        self._store: Dict[str, LWWEntry] = {}
        self._dirty_keys: Set[str] = set()
        self._skew_conflicts: Dict[str, Tuple[LWWEntry, LWWEntry]] = {}
        self._logical_counter: int = 0

    def _compare_and_resolve(
        self,
        key: str,
        local: Optional[LWWEntry],
        new_timestamp: HybridTimestamp,
        new_value: Any,
        new_device_id: str,
    ) -> Optional[ClockSkewConflict]:
        """Apply add-wins comparison and detect clock skew.

        Returns conflict if skew exceeds threshold, None otherwise.
        """
        new_entry = LWWEntry(value=new_value, timestamp=new_timestamp, device_id=new_device_id)

        if local is None:
            self._store[key] = new_entry
            self._dirty_keys.add(key)
            return None

        # Clock skew detection
        skew_ns = abs(new_timestamp.physical - local.timestamp.physical)
        conflict: Optional[ClockSkewConflict] = None
        if skew_ns > MAX_CLOCK_SKEW_NS:
            conflict = ClockSkewConflict(
                key=key,
                local_entry=local,
                remote_entry=new_entry,
            )
            self._skew_conflicts[key] = (local, new_entry)
            logger.warning(
                "Clock skew detected for key '{}': {}ns > {}ns",
                key,
                skew_ns,
                MAX_CLOCK_SKEW_NS,
            )
            # Conflict edge soft limit alarm
            if len(self._skew_conflicts) > MAX_CONTRADICT_KEYS:
                logger.warning(
                    "LWWMap skew-conflicted keys exceed soft limit {} (current: {})",
                    MAX_CONTRADICT_KEYS,
                    len(self._skew_conflicts),
                )

        # Add-wins: keep entry with larger HLC
        if new_timestamp > local.timestamp:
            self._store[key] = new_entry
            self._dirty_keys.add(key)
        elif new_timestamp == local.timestamp and new_device_id > local.device_id:
            # Tie-break by device_id lexicographic order for determinism
            self._store[key] = new_entry
            self._dirty_keys.add(key)

        return conflict

    def set(
        self,
        key: str,
        value: Any,
        timestamp: Optional[HybridTimestamp] = None,
        device_id: Optional[str] = None,
    ) -> Optional[ClockSkewConflict]:
        """Set key using add-wins semantics.

        If clock skew exceeds MAX_CLOCK_SKEW_NS, record conflict but still
        apply HLC winner.
        """
        local = self._store.get(key)
        resolved_device_id = device_id if device_id is not None else self.device_id
        if timestamp is None:
            self._logical_counter += 1
            timestamp = HybridTimestamp.now(logical=self._logical_counter)
        return self._compare_and_resolve(
            key=key,
            local=local,
            new_timestamp=timestamp,
            new_value=value,
            new_device_id=resolved_device_id,
        )

    def get(self, key: str) -> Any:
        """Return current value for key.

        Raises:
            KeyError: If key does not exist.
        """
        if key not in self._store:
            raise KeyError(f"Key '{key}' not found in LWWMap")
        return self._store[key].value

    def get_entry(self, key: str) -> LWWEntry:
        """Return raw LWWEntry for key.

        Raises:
            KeyError: If key does not exist.
        """
        if key not in self._store:
            raise KeyError(f"Key '{key}' not found in LWWMap")
        return self._store[key]

    def merge(self, remote_entries: Dict[str, LWWEntry]) -> List[ClockSkewConflict]:
        """Merge remote state into local map.

        For each key, apply add-wins comparison. If clock skew detected,
        keep local winner but record conflict for upstream CONTRADICTS edge creation.

        Returns:
            List of detected clock-skew conflicts.
        """
        conflicts: List[ClockSkewConflict] = []
        for key, remote_entry in remote_entries.items():
            local = self._store.get(key)
            self._logical_counter += 1
            conflict = self._compare_and_resolve(
                key=key,
                local=local,
                new_timestamp=remote_entry.timestamp,
                new_value=remote_entry.value,
                new_device_id=remote_entry.device_id,
            )
            if conflict is not None:
                conflicts.append(conflict)
        return conflicts

    def get_delta(self, since_vector_clock: Optional[Dict[str, int]] = None) -> Dict[str, LWWEntry]:
        """Return entries newer than given vector clock.

        If since_vector_clock is None, return all entries.
        """
        if since_vector_clock is None:
            return dict(self._store)

        delta: Dict[str, LWWEntry] = {}
        for key, entry in self._store.items():
            remote_ts = since_vector_clock.get(entry.device_id, 0)
            if entry.timestamp.physical > remote_ts:
                delta[key] = entry
        return delta

    def checkpoint(self) -> List[str]:
        """Return list of dirty keys and clear the dirty set.

        Returns:
            Snapshot of keys pending persistence.
        """
        keys = list(self._dirty_keys)
        self._dirty_keys.clear()
        self._skew_conflicts.clear()
        return keys

    def get_skew_conflicts(self) -> Dict[str, Tuple[LWWEntry, LWWEntry]]:
        """Return all recorded skew conflicts since last checkpoint."""
        return dict(self._skew_conflicts)
