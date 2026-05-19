"""Mock BGE embedder for L2 episodic memory."""

from chronopersona.contracts.interfaces.abstract_embedder import AbstractEmbedder


class MockBGEEmbedder(AbstractEmbedder):
    """Mock embedder that returns deterministic vectors based on text length."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate mock embeddings."""
        return [self._mock_vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        """Generate mock query embedding."""
        text = text or ""
        return self._mock_vector(text)

    @staticmethod
    def _mock_vector(text: str) -> list[float]:
        """Create a deterministic mock vector from text."""
        # Use a simple hash-based approach for reproducibility
        seed = sum(ord(c) for c in text)
        dim = 128  # Reduced dimension for mock
        return [(seed * (i + 1) % 1000) / 1000.0 for i in range(dim)]
