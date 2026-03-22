"""
Loads data/full_dataset.csv and exposes lookups for pregame statistics.

All team stats must come from this historical dataset—no hardcoded team stats.
Functions will resolve team name + game date to the most recent applicable row(s).
"""
from typing import Any, Dict, Optional

_dataset = None  # Will hold loaded DataFrame or similar


def load_dataset() -> None:
    """Load full_dataset.csv once at startup or on first use."""
    pass


def get_team_pregame_stats(team_name: str, game_date: str) -> Optional[Dict[str, Any]]:
    """Return the most recent pregame stat row for team_name as of game_date."""
    pass
