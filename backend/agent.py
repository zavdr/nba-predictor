"""
Claude (Anthropic) agent with tool use / function calling.

The agent will receive team pregame stats, define tools to assemble model features,
call the sklearn predictor via tools, and produce a natural-language explanation of
the win probability. Uses the Messages API with tool_choice, not prompt-only text.
"""
from typing import Any, Dict, List


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Return Anthropic tool schemas for feature assembly and model prediction."""
    pass


def run_agent(
    home_team: str,
    away_team: str,
    game_date: str,
    home_stats: Dict[str, Any],
    away_stats: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Run the Claude agent loop: tool calls to build features, predict, then explanation.
    Returns keys such as win_probability, predicted_winner, and explanation text.
    """
    pass
