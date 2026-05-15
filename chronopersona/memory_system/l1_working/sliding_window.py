"""L1 Working Memory sliding window with dynamic compression."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import List, Optional, Protocol

from loguru import logger


@dataclass
class TurnEntry:
    """A single dialogue turn in L1 working memory."""

    turn_id: int
    user_text: str
    agent_text: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    token_count: int = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.token_count = self._estimate_tokens(self.user_text) + self._estimate_tokens(self.agent_text)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Naive token estimation for MVA: Chinese chars + English words."""
        cn_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        en_tokens = len(re.findall(r"[a-zA-Z]+", text))
        return cn_chars + en_tokens

    def to_text(self) -> str:
        """Serialize turn to conversation text."""
        return f"User: {self.user_text}\nAgent: {self.agent_text}"


@dataclass
class CompressedSummary:
    """Summary of compressed turns, kept in L1 only (not vector store)."""

    summary_id: str
    source_turn_ids: list[int]
    content: str
    created_at: datetime
    token_count: int


class Compressor(Protocol):
    """Protocol for turn compression strategy (e.g., LLM summarizer)."""

    def __call__(self, turns: list[TurnEntry]) -> str:
        """Compress a batch of turns into a single summary string."""


class _NaiveCompressor:
    """Fallback compressor when no LLM is available."""

    def __call__(self, turns: list[TurnEntry]) -> str:
        snippets = [t.to_text() for t in turns]
        joined = " | ".join(snippets)
        return "[Compressed] " + joined[:200] + "..."


class WorkingMemoryWindow:
    """L1 Working Memory: sliding window with dynamic compression."""

    def __init__(
        self,
        branch_id: str,
        session_id: str,
        max_turns: int = 10,
        token_threshold: int = 4096,
        compressor: Compressor | None = None,
    ) -> None:
        if not branch_id:
            raise ValueError("branch_id must not be empty")
        if not session_id:
            raise ValueError("session_id must not be empty")

        self.branch_id: str = branch_id
        self.session_id: str = session_id
        self.max_turns: int = max_turns
        self.token_threshold: int = token_threshold
        self._compressor: Compressor = compressor or _NaiveCompressor()
        self._turns: list[TurnEntry] = []
        self._compressed_summaries: list[CompressedSummary] = []
        self._next_turn_id: int = 1

    def add_turn(self, user_text: str, agent_text: str) -> None:
        """Add a new dialogue turn and trigger compression if thresholds exceeded."""
        turn = TurnEntry(
            turn_id=self._next_turn_id,
            user_text=user_text,
            agent_text=agent_text,
        )
        self._next_turn_id += 1
        self._turns.append(turn)
        logger.debug(
            "L1 turn {} added (tokens={}, branch={}, session={})",
            turn.turn_id,
            turn.token_count,
            self.branch_id,
            self.session_id,
        )

        if self.total_tokens > self.token_threshold:
            self._compress_oldest_for_token_relief()
        if len(self._turns) > self.max_turns:
            self._compress_oldest_batch()

    @property
    def total_tokens(self) -> int:
        """Return total token count across active turns and compressed summaries."""
        turn_tokens = sum(t.token_count for t in self._turns)
        summary_tokens = sum(s.token_count for s in self._compressed_summaries)
        return turn_tokens + summary_tokens

    def _compress_oldest_for_token_relief(self) -> None:
        """Compress oldest turns until total_tokens <= token_threshold."""
        safety = 0
        while self._turns and self.total_tokens > self.token_threshold and safety < 100:
            batch_size = max(1, len(self._turns) // 2)
            self._compress_batch(self._turns[:batch_size])
            safety += 1
        if safety >= 100:
            logger.error("L1 compression loop exceeded safety limit")

    def _compress_oldest_batch(self) -> None:
        """Compress the oldest batch to satisfy max_turns constraint."""
        overflow = len(self._turns) - self.max_turns
        if overflow <= 0:
            return
        batch_size = max(1, overflow)
        self._compress_batch(self._turns[:batch_size])

    def _compress_batch(self, turns_to_compress: list[TurnEntry]) -> None:
        """Compress a list of turns into a single CompressedSummary."""
        if not turns_to_compress:
            return

        content = self._compressor(turns_to_compress)
        summary = CompressedSummary(
            summary_id=f"sum-{uuid.uuid4().hex[:8]}",
            source_turn_ids=[t.turn_id for t in turns_to_compress],
            content=content,
            created_at=datetime.now(UTC),
            token_count=len(content),
        )
        self._compressed_summaries.append(summary)

        remove_ids = {t.turn_id for t in turns_to_compress}
        self._turns = [t for t in self._turns if t.turn_id not in remove_ids]

        logger.info(
            "L1 compressed turns {} -> summary {} ({} tokens, branch={})",
            summary.source_turn_ids,
            summary.summary_id,
            summary.token_count,
            self.branch_id,
        )

    def get_context(self, token_limit: int | None = None) -> list[TurnEntry | CompressedSummary]:
        """Return context items in reverse chronological order (newest first)."""
        items: list[TurnEntry | CompressedSummary] = []

        for turn in reversed(self._turns):
            items.append(turn)

        for summary in reversed(self._compressed_summaries):
            items.append(summary)

        if token_limit is None:
            return items

        result: list[TurnEntry | CompressedSummary] = []
        current_tokens = 0
        for item in items:
            cost = item.token_count
            if current_tokens + cost > token_limit:
                break
            result.append(item)
            current_tokens += cost

        return result

    def should_compress(self) -> bool:
        """Return True if compression thresholds are currently exceeded."""
        return len(self._turns) > self.max_turns or self.total_tokens > self.token_threshold

    def snapshot(self) -> dict:
        """Return a serializable snapshot for debugging/tests."""
        return {
            "branch_id": self.branch_id,
            "session_id": self.session_id,
            "turn_count": len(self._turns),
            "summary_count": len(self._compressed_summaries),
            "total_tokens": self.total_tokens,
            "turn_ids": [t.turn_id for t in self._turns],
            "summary_ids": [s.summary_id for s in self._compressed_summaries],
        }
