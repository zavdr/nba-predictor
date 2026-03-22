import joblib
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'model', 'nba_model.pkl')
FEATURES_PATH = os.path.join(BASE_DIR, 'model', 'nba_features.pkl')

model = joblib.load(MODEL_PATH)
FEATURES = joblib.load(FEATURES_PATH)


def predict(home_stats: dict, away_stats: dict) -> dict:
    row = {
        'HOME_LAST5_WIN': home_stats['last5_win'],
        'AWAY_LAST5_WIN': away_stats['last5_win'],
        'HOME_WIN_PCT':   home_stats['win_pct'],
        'AWAY_WIN_PCT':   away_stats['win_pct'],
        'HOME_REST_DAYS': home_stats['rest_days'],
        'AWAY_REST_DAYS': away_stats['rest_days'],
        'HOME_AVG_PTS':   home_stats['avg_pts'],
        'AWAY_AVG_PTS':   away_stats['avg_pts'],
    }

    X = pd.DataFrame([row])[FEATURES]

    home_win_prob = float(model.predict_proba(X)[0][1])
    away_win_prob = 1 - home_win_prob

    predicted_winner = home_stats['team'] if home_win_prob >= 0.5 else away_stats['team']

    return {
        'predicted_winner':     predicted_winner,
        'home_win_probability': round(home_win_prob * 100, 1),
        'away_win_probability': round(away_win_prob * 100, 1),
        'home_team':            home_stats['team'],
        'away_team':            away_stats['team'],
    }
