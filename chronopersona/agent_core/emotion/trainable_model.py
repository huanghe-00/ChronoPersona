"""Trainable emotion model — LSTM regressor placeholder.

Layer 2 of Emotion Engine. W5: Skeleton only. W8+ full implementation.
"""

from typing import List, Optional, Tuple

from loguru import logger


class TrainableEmotionModel:
    """LSTM-based emotion intensity regressor.

    [RL-PLACEHOLDER]: Future PPO/GRPO optimization hook reserved.
    """

    def __init__(self, input_dim: int = 768, hidden_dim: int = 128) -> None:
        self._input_dim = input_dim
        self._hidden_dim = hidden_dim
        self._model: Optional[object] = None  # TODO(W8): Load LSTM weights

    def predict(self, context_texts: List[str]) -> float:
        """Predict emotion intensity from last 5 turns.

        Args:
            context_texts: List of text strings (last N dialogue turns).

        Returns:
            Intensity value [-1.0, 1.0]. MVA: returns deterministic mock.

        TODO(W8): Replace with actual LSTM forward pass.
        """
        logger.info(
            "TrainableEmotionModel.predict: {} turns (MOCK)",
            len(context_texts),
        )
        text = " ".join(context_texts).lower()
        if any(w in text for w in ["难过", "伤心", "痛苦", "焦虑"]):
            return -0.7
        if any(w in text for w in ["开心", "高兴", "兴奋", "喜欢"]):
            return 0.7
        return 0.0

    def train_step(self, batch: List[Tuple[str, float]]) -> None:
        """Single training step.

        [RL-PLACEHOLDER]: Skeleton for future RLHF/PPO loop.
        TODO(W8): Implement BERT encoding + LSTM backprop.
        """
        logger.info("TrainableEmotionModel.train_step: {} samples (NO-OP)", len(batch))
        pass

    def save_checkpoint(self, path: str) -> None:
        """Save model weights.

        TODO(W8): torch.save(self._model.state_dict(), path).
        """
        logger.info("TrainableEmotionModel.save_checkpoint: {} (NO-OP)", path)

    def load_checkpoint(self, path: str) -> None:
        """Load model weights.

        TODO(W8): self._model.load_state_dict(torch.load(path)).
        """
        logger.info("TrainableEmotionModel.load_checkpoint: {} (NO-OP)", path)
