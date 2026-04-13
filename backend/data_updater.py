from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import date
import json
from pathlib import Path
import ssl
from typing import Iterable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

try:
    import certifi
except ImportError:
    certifi = None


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "full_dataset.csv"
NBA_STATS_URL = "https://stats.nba.com/stats/leaguegamefinder"
NBA_STATS_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
}
DEFAULT_TEAM_STATE = {
    "games_played": 0,
    "games_won": 0,
    "win_pct": 0.5,
    "avg_pts": 110.0,
    "last5_win": 0.5,
    "rest_days": 3,
}


@dataclass
class TeamState:
    games_played: int = 0
    wins: int = 0
    total_points: int = 0
    last_results: deque[int] = field(default_factory=lambda: deque(maxlen=5))
    last_game_date: pd.Timestamp | None = None

    def pregame_snapshot(self, game_date: pd.Timestamp) -> dict[str, float | int]:
        if self.games_played == 0:
            snapshot = DEFAULT_TEAM_STATE.copy()
        else:
            snapshot = {
                "games_played": self.games_played,
                "games_won": self.wins,
                "win_pct": round(self.wins / self.games_played, 6),
                "avg_pts": round(self.total_points / self.games_played, 1),
                "last5_win": round(sum(self.last_results) / len(self.last_results), 3),
                "rest_days": 3,
            }

        if self.last_game_date is not None:
            snapshot["rest_days"] = int((game_date - self.last_game_date).days)

        return snapshot

    def record_game(self, game_date: pd.Timestamp, points: int, won: int) -> None:
        self.games_played += 1
        self.wins += int(won)
        self.total_points += int(points)
        self.last_results.append(int(won))
        self.last_game_date = game_date


def _read_existing_dataset(csv_path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"]).dt.normalize()
    return df


def _format_date_for_api(value: date) -> str:
    return value.strftime("%m/%d/%Y")


def _season_label_for_date(value: date | pd.Timestamp) -> str:
    value = pd.Timestamp(value)
    start_year = value.year if value.month >= 10 else value.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def _season_labels_between(start_date: date, end_date: date) -> list[str]:
    labels = []
    start_year = start_date.year - 1
    end_year = end_date.year + 1

    for year in range(start_year, end_year + 1):
        label = f"{year}-{str(year + 1)[-2:]}"
        season_start = date(year, 10, 1)
        season_end = date(year + 1, 6, 30)
        if season_end >= start_date and season_start <= end_date:
            labels.append(label)

    return labels


def _extract_result_set(payload: dict, name: str) -> dict:
    result_sets = payload.get("resultSets") or payload.get("resultSet") or []
    if isinstance(result_sets, dict):
        result_sets = [result_sets]

    for result_set in result_sets:
        if result_set.get("name") == name:
            return result_set

    raise ValueError(f"Result set {name} was not found in the NBA stats response.")


def fetch_team_game_logs(
    start_date: date,
    end_date: date | None = None,
    season_type: str = "Regular Season",
) -> pd.DataFrame:
    if end_date is None:
        end_date = date.today()

    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")

    frames: list[pd.DataFrame] = []
    ssl_context = (
        ssl.create_default_context(cafile=certifi.where())
        if certifi is not None
        else ssl.create_default_context()
    )

    for season in _season_labels_between(start_date, end_date):
        query = urlencode(
            {
                "PlayerOrTeam": "T",
                "LeagueID": "00",
                "Season": season,
                "SeasonType": season_type,
                "DateFrom": _format_date_for_api(start_date),
                "DateTo": _format_date_for_api(end_date),
            }
        )
        request = Request(
            f"{NBA_STATS_URL}?{query}",
            headers=NBA_STATS_HEADERS,
        )
        with urlopen(request, timeout=30, context=ssl_context) as response:
            payload = json.load(response)

            result_set = _extract_result_set(payload, "LeagueGameFinderResults")
            frame = pd.DataFrame(result_set["rowSet"], columns=result_set["headers"])
            if not frame.empty:
                frames.append(frame)

    if not frames:
        return pd.DataFrame()

    game_logs = pd.concat(frames, ignore_index=True)
    game_logs["GAME_DATE"] = pd.to_datetime(game_logs["GAME_DATE"]).dt.normalize()
    game_logs["PTS"] = game_logs["PTS"].astype(int)
    game_logs = game_logs.drop_duplicates(subset=["GAME_ID", "TEAM_ID"]).sort_values(
        ["GAME_DATE", "GAME_ID", "TEAM_ID"]
    )
    return game_logs.reset_index(drop=True)


def _initialize_team_states(existing_df: pd.DataFrame) -> tuple[str, dict[str, TeamState]]:
    latest_row = existing_df.sort_values(["GAME_DATE", "GAME_ID"]).iloc[-1]
    latest_season = str(latest_row["SEASON"])
    season_df = existing_df[existing_df["SEASON"].astype(str) == latest_season].copy()
    season_df = season_df.sort_values(["GAME_DATE", "GAME_ID"])

    states: dict[str, TeamState] = {}
    for row in season_df.itertuples(index=False):
        game_date = pd.Timestamp(row.GAME_DATE).normalize()
        home_state = states.setdefault(row.HOME, TeamState())
        away_state = states.setdefault(row.AWAY, TeamState())

        home_state.record_game(game_date, int(row.HOME_PTS), int(row.HOME_WIN))
        away_state.record_game(game_date, int(row.AWAY_PTS), int(row.AWAY_WL))

    return latest_season, states


def _is_home_team(matchup: str) -> bool:
    return " vs. " in matchup


def _pair_game_rows(game_logs: pd.DataFrame) -> Iterable[tuple[pd.Series, pd.Series]]:
    for _, game_rows in game_logs.groupby("GAME_ID", sort=False):
        if len(game_rows) != 2:
            continue

        home_rows = game_rows[game_rows["MATCHUP"].apply(_is_home_team)]
        away_rows = game_rows[~game_rows["MATCHUP"].apply(_is_home_team)]
        if len(home_rows) != 1 or len(away_rows) != 1:
            continue

        yield home_rows.iloc[0], away_rows.iloc[0]


def _build_rows_from_game_logs(
    existing_df: pd.DataFrame,
    game_logs: pd.DataFrame,
) -> pd.DataFrame:
    if game_logs.empty:
        return pd.DataFrame(columns=existing_df.columns)

    existing_game_ids = set(existing_df["GAME_ID"].astype(str))
    latest_existing_season, team_states = _initialize_team_states(existing_df)
    current_season = latest_existing_season

    rows: list[dict] = []
    for home_row, away_row in _pair_game_rows(game_logs.sort_values(["GAME_DATE", "GAME_ID"])):
        game_id = str(home_row["GAME_ID"])
        if game_id in existing_game_ids:
            continue

        game_date = pd.Timestamp(home_row["GAME_DATE"]).normalize()
        season = _season_label_for_date(game_date)
        if season != current_season:
            team_states = {}
            current_season = season

        home_team = str(home_row["TEAM_ABBREVIATION"])
        away_team = str(away_row["TEAM_ABBREVIATION"])
        home_state = team_states.setdefault(home_team, TeamState())
        away_state = team_states.setdefault(away_team, TeamState())

        home_snapshot = home_state.pregame_snapshot(game_date)
        away_snapshot = away_state.pregame_snapshot(game_date)

        home_win = 1 if str(home_row["WL"]).upper() == "W" else 0
        away_win = 1 if str(away_row["WL"]).upper() == "W" else 0

        rows.append(
            {
                "GAME_ID": int(home_row["GAME_ID"]),
                "GAME_DATE": game_date.strftime("%Y-%m-%d"),
                "HOME": home_team,
                "HOME_WIN": home_win,
                "HOME_PTS": int(home_row["PTS"]),
                "AWAY": away_team,
                "AWAY_WL": away_win,
                "AWAY_PTS": int(away_row["PTS"]),
                "HOME_GP": int(home_snapshot["games_played"]),
                "AWAY_GP": int(away_snapshot["games_played"]),
                "HOME_GAMES_WON": int(home_snapshot["games_won"]),
                "AWAY_GAMES_WON": int(away_snapshot["games_won"]),
                "HOME_WIN_PCT": float(home_snapshot["win_pct"]),
                "AWAY_WIN_PCT": float(away_snapshot["win_pct"]),
                "HOME_AVG_PTS": float(home_snapshot["avg_pts"]),
                "AWAY_AVG_PTS": float(away_snapshot["avg_pts"]),
                "HOME_LAST5_WIN": float(home_snapshot["last5_win"]),
                "HOME_REST_DAYS": int(home_snapshot["rest_days"]),
                "AWAY_LAST5_WIN": float(away_snapshot["last5_win"]),
                "AWAY_REST_DAYS": int(away_snapshot["rest_days"]),
                "SEASON": season,
            }
        )

        home_state.record_game(game_date, int(home_row["PTS"]), home_win)
        away_state.record_game(game_date, int(away_row["PTS"]), away_win)

    if not rows:
        return pd.DataFrame(columns=existing_df.columns)

    return pd.DataFrame(rows)[existing_df.columns]


def append_latest_games_to_dataset(
    csv_path: str | Path = DATA_PATH,
    end_date: date | None = None,
) -> pd.DataFrame:
    csv_path = Path(csv_path)
    existing_df = _read_existing_dataset(csv_path)
    latest_existing_date = existing_df["GAME_DATE"].max().date()
    fetch_start_date = latest_existing_date

    if end_date is None:
        end_date = date.today()

    game_logs = fetch_team_game_logs(fetch_start_date, end_date=end_date)
    new_rows = _build_rows_from_game_logs(existing_df, game_logs)
    if new_rows.empty:
        return new_rows

    combined = pd.concat([existing_df, new_rows], ignore_index=True)
    combined = combined.drop_duplicates(subset=["GAME_ID"], keep="first")
    combined["GAME_DATE"] = pd.to_datetime(combined["GAME_DATE"]).dt.strftime("%Y-%m-%d")
    combined = combined.sort_values(["GAME_DATE", "GAME_ID"])
    combined.to_csv(csv_path, index=False)
    return new_rows.reset_index(drop=True)


if __name__ == "__main__":
    appended_rows = append_latest_games_to_dataset()
    print(f"Appended {len(appended_rows)} new games to {DATA_PATH}.")
