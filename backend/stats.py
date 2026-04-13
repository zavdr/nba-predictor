import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'full_dataset.csv')

df = pd.DataFrame()
ALL_TEAMS = []


def refresh_dataset() -> None:
    global df, ALL_TEAMS

    df = pd.read_csv(DATA_PATH)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    ALL_TEAMS = sorted(set(df['HOME'].unique()) | set(df['AWAY'].unique()))


refresh_dataset()


def get_team_stats(team: str, date: str) -> dict:
    query_date = pd.to_datetime(date)

    home_games = df[(df['HOME'] == team) & (
        df['GAME_DATE'] < query_date)].copy()
    home_games = home_games.rename(columns={
        'HOME_WIN_PCT':   'WIN_PCT',
        'HOME_AVG_PTS':   'AVG_PTS',
        'HOME_LAST5_WIN': 'LAST5_WIN',
        'HOME_REST_DAYS': 'REST_DAYS',
        'HOME_WIN':       'WIN',
        'HOME_PTS':       'PTS'
    })[['GAME_DATE', 'WIN_PCT', 'AVG_PTS', 'LAST5_WIN', 'REST_DAYS', 'WIN', 'PTS']]

    away_games = df[(df['AWAY'] == team) & (
        df['GAME_DATE'] < query_date)].copy()
    away_games = away_games.rename(columns={
        'AWAY_WIN_PCT':   'WIN_PCT',
        'AWAY_AVG_PTS':   'AVG_PTS',
        'AWAY_LAST5_WIN': 'LAST5_WIN',
        'AWAY_REST_DAYS': 'REST_DAYS',
        'AWAY_WL':        'WIN',
        'AWAY_PTS':       'PTS'
    })[['GAME_DATE', 'WIN_PCT', 'AVG_PTS', 'LAST5_WIN', 'REST_DAYS', 'WIN', 'PTS']]

    all_games = pd.concat([home_games, away_games]).sort_values('GAME_DATE')

    if all_games.empty:
        return {
            'team':      team,
            'win_pct':   0.5,
            'avg_pts':   110.0,
            'last5_win': 0.5,
            'rest_days': 3,
            'games_played': 0
        }

    latest = all_games.iloc[-1]

    return {
        'team':         team,
        'win_pct':      round(float(latest['WIN_PCT']), 3),
        'avg_pts':      round(float(latest['AVG_PTS']), 1),
        'last5_win':    round(float(latest['LAST5_WIN']), 3),
        'rest_days':    int(latest['REST_DAYS']),
        'games_played': len(all_games)
    }


def get_all_teams() -> list:
    return ALL_TEAMS
