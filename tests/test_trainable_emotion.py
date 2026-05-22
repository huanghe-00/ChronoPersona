"""Unit tests for TrainableEmotionModel (Layer 2 skeleton)."""

import pytest

from chronopersona.agent_core.emotion.trainable_model import TrainableEmotionModel


class TestTrainableEmotionModel:
    """Tests for LSTM regressor skeleton and data utilities."""

    def test_predict_returns_float_in_range(self) -> None:
        """T01: predict returns float within [-1.0, 1.0]."""
        model = TrainableEmotionModel()
        result = model.predict(["今天天气不错"])
        assert isinstance(result, float)
        assert -1.0 <= result <= 1.0

    def test_predict_negative_text(self) -> None:
        """T02: Negative text returns negative intensity."""
        model = TrainableEmotionModel()
        result = model.predict(["我最近很焦虑"])
        assert result < 0.0

    def test_predict_positive_text(self) -> None:
        """T03: Positive text returns positive intensity."""
        model = TrainableEmotionModel()
        result = model.predict(["今天真开心"])
        assert result > 0.0

    def test_prepare_training_data_pairs_correctly(self) -> None:
        """T04: prepare_training_data zips texts and labels."""
        model = TrainableEmotionModel()
        data = model.prepare_training_data(["a", "b", "c"], [1.0, 0.0, -1.0])
        assert len(data) == 3
        assert data[0] == ("a", 1.0)
        assert data[2] == ("c", -1.0)

    def test_prepare_training_data_length_mismatch_raises(self) -> None:
        """T05: Mismatched lengths raise ValueError."""
        model = TrainableEmotionModel()
        with pytest.raises(ValueError):
            model.prepare_training_data(["a", "b"], [1.0])

    def test_fit_empty_data_raises_valueerror(self) -> None:
        """T06: fit with empty data raises ValueError."""
        model = TrainableEmotionModel()
        with pytest.raises(ValueError):
            model.fit([])

    def test_fit_runs_without_error(self) -> None:
        """T07: fit executes no-op loop without error."""
        model = TrainableEmotionModel()
        data = [("hello", 0.5), ("world", -0.5)]
        model.fit(data, epochs=2)  # Should not raise
