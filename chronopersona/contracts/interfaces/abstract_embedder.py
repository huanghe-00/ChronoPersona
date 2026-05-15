"""Abstract interface for embedding models."""

from abc import ABC, abstractmethod
from typing import List


class AbstractEmbedder(ABC):
    """Interface for text embedding models."""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of input strings.

        Returns:
            List of embedding vectors, each as a list of floats.
        """
        ...

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query text.

        Args:
            text: Input query string.

        Returns:
            Embedding vector as a list of floats.
        """
        ...
