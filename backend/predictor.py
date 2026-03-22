"""
Loads the pre-trained scikit-learn pipeline from model/nba_model.pkl.

Exposes predict(features) returning home-team win probability (0.0–1.0).
Do not retrain here; only load and inference.
"""
from typing import Any


_pipeline = None  # Will hold joblib-loaded sklearn Pipeline


def load_model() -> None:
    """Load model/nba_model.pkl once at startup or on first use."""
    pass


def predict(features: Any) -> float:
    """Run the loaded pipeline on assembled feature vector; return P(home win)."""
    pass
