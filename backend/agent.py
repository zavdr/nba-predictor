import json
import os
from stats import get_team_stats
from predictor import predict


def run_agent(home_team: str, away_team: str, game_date: str) -> dict:
    home_stats = get_team_stats(home_team, game_date)
    away_stats = get_team_stats(away_team, game_date)

    result = predict(home_stats, away_stats)

    home_win_prob = result['home_win_probability']
    away_win_prob = result['away_win_probability']
    winner = result['predicted_winner']

    factors = []

    if home_stats['win_pct'] > away_stats['win_pct'] + 0.05:
        factors.append(
            f"{home_team} has a better season record ({home_stats['win_pct']:.0%} vs {away_stats['win_pct']:.0%})")
    elif away_stats['win_pct'] > home_stats['win_pct'] + 0.05:
        factors.append(
            f"{away_team} has a better season record ({away_stats['win_pct']:.0%} vs {home_stats['win_pct']:.0%})")

    if home_stats['last5_win'] > away_stats['last5_win'] + 0.2:
        factors.append(
            f"{home_team} is in better recent form ({home_stats['last5_win']:.0%} vs {away_stats['last5_win']:.0%} last 5)")
    elif away_stats['last5_win'] > home_stats['last5_win'] + 0.2:
        factors.append(
            f"{away_team} is in better recent form ({away_stats['last5_win']:.0%} vs {home_stats['last5_win']:.0%} last 5)")

    if home_stats['rest_days'] > away_stats['rest_days'] + 1:
        factors.append(
            f"{home_team} has more rest ({home_stats['rest_days']} days vs {away_stats['rest_days']})")
    elif away_stats['rest_days'] > home_stats['rest_days'] + 1:
        factors.append(
            f"{away_team} has more rest ({away_stats['rest_days']} days vs {home_stats['rest_days']})")

    if home_stats['avg_pts'] > away_stats['avg_pts'] + 3:
        factors.append(
            f"{home_team} scores more on average ({home_stats['avg_pts']:.1f} vs {away_stats['avg_pts']:.1f} ppg)")
    elif away_stats['avg_pts'] > home_stats['avg_pts'] + 3:
        factors.append(
            f"{away_team} scores more on average ({away_stats['avg_pts']:.1f} vs {home_stats['avg_pts']:.1f} ppg)")

    if not factors:
        factors.append("Teams are evenly matched — close game expected")

    explanation = f"{winner} is predicted to win with {max(home_win_prob, away_win_prob):.1f}% probability. " + " ".join(
        factors) + "."

    return {
        'predicted_winner':      winner,
        'home_win_probability':  home_win_prob,
        'away_win_probability':  away_win_prob,
        'home_team':             home_team,
        'away_team':             away_team,
        'explanation':           explanation
    }
