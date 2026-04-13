from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pandas as pd

try:
    import certifi
except ImportError:
    certifi = None


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "full_dataset.csv"
ESPN_SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
DATE_CHUNK_DAYS = 30
NBA_CALENDAR_TIMEZONE = ZoneInfo("America/New_York")
ESPN_TO_DATASET_ABBREVIATIONS = {
    "GS": "GSW",
    "NO": "NOP",
    "NY": "NYK",
    "SA": "SAS",
    "UTAH": "UTA",
    "WSH": "WAS",
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


def _season_label_for_date(value: date | pd.Timestamp) -> str:
    value = pd.Timestamp(value)
    start_year = value.year if value.month >= 10 else value.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def _normalize_team_abbreviation(abbreviation: str) -> str:
    return ESPN_TO_DATASET_ABBREVIATIONS.get(abbreviation, abbreviation)


def _iter_date_chunks(start_date: date, end_date: date, chunk_days: int = DATE_CHUNK_DAYS):
    current = start_date
    while current <= end_date:
        chunk_end = min(current + timedelta(days=chunk_days - 1), end_date)
        yield current, chunk_end
        current = chunk_end + timedelta(days=1)


def _format_espn_dates_param(start_date: date, end_date: date) -> str:
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    return start_str if start_str == end_str else f"{start_str}-{end_str}"


def fetch_completed_regular_season_games(
    start_date: date,
    end_date: date | None = None,
) -> pd.DataFrame:
    if end_date is None:
        end_date = date.today()

    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date.")

    verify_path = certifi.where() if certifi is not None else True
    rows: list[dict] = []

    with httpx.Client(timeout=20.0, verify=verify_path, follow_redirects=True) as client:
        for chunk_start, chunk_end in _iter_date_chunks(start_date, end_date):
            response = client.get(
                ESPN_SCOREBOARD_URL,
                params={"dates": _format_espn_dates_param(chunk_start, chunk_end)},
            )
            response.raise_for_status()
            payload = response.json()

            for event in payload.get("events", []):
                season = event.get("season", {})
                competition = event.get("competitions", [{}])[0]
                status = competition.get("status", {}).get("type", {})

                if season.get("type") != 2:
                    continue

                if not status.get("completed"):
                    continue

                home = next(
                    competitor
                    for competitor in competition.get("competitors", [])
                    if competitor.get("homeAway") == "home"
                )
                away = next(
                    competitor
                    for competitor in competition.get("competitors", [])
                    if competitor.get("homeAway") == "away"
                )

                game_date = (
                    pd.to_datetime(event["date"], utc=True)
                    .tz_convert(NBA_CALENDAR_TIMEZONE)
                    .normalize()
                    .tz_localize(None)
                )

                rows.append(
                    {
                        "GAME_ID": int(event["id"]),
                        "GAME_DATE": game_date,
                        "HOME": _normalize_team_abbreviation(home["team"]["abbreviation"]),
                        "HOME_WIN": int(bool(home.get("winner"))),
                        "HOME_PTS": int(home["score"]),
                        "AWAY": _normalize_team_abbreviation(away["team"]["abbreviation"]),
                        "AWAY_WL": int(bool(away.get("winner"))),
                        "AWAY_PTS": int(away["score"]),
                    }
                )

    if not rows:
        return pd.DataFrame()

    games = pd.DataFrame(rows)
    games = games.drop_duplicates(subset=["GAME_ID"]).sort_values(["GAME_DATE", "GAME_ID"])
    return games.reset_index(drop=True)


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


def _build_rows_from_completed_games(
    existing_df: pd.DataFrame,
    completed_games: pd.DataFrame,
) -> pd.DataFrame:
    if completed_games.empty:
        return pd.DataFrame(columns=existing_df.columns)

    existing_game_ids = set(existing_df["GAME_ID"].astype(int))
    latest_existing_season, team_states = _initialize_team_states(existing_df)
    current_season = latest_existing_season
    rows: list[dict] = []

    for game in completed_games.sort_values(["GAME_DATE", "GAME_ID"]).itertuples(index=False):
        game_id = int(game.GAME_ID)
        if game_id in existing_game_ids:
            continue

        game_date = pd.Timestamp(game.GAME_DATE).normalize()
        season = _season_label_for_date(game_date)
        if season != current_season:
            team_states = {}
            current_season = season

        home_state = team_states.setdefault(game.HOME, TeamState())
        away_state = team_states.setdefault(game.AWAY, TeamState())
        home_snapshot = home_state.pregame_snapshot(game_date)
        away_snapshot = away_state.pregame_snapshot(game_date)

        rows.append(
            {
                "GAME_ID": game_id,
                "GAME_DATE": game_date.strftime("%Y-%m-%d"),
                "HOME": game.HOME,
                "HOME_WIN": int(game.HOME_WIN),
                "HOME_PTS": int(game.HOME_PTS),
                "AWAY": game.AWAY,
                "AWAY_WL": int(game.AWAY_WL),
                "AWAY_PTS": int(game.AWAY_PTS),
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

        home_state.record_game(game_date, int(game.HOME_PTS), int(game.HOME_WIN))
        away_state.record_game(game_date, int(game.AWAY_PTS), int(game.AWAY_WL))

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
    fetch_start_date = latest_existing_date + timedelta(days=1)

    if end_date is None:
        end_date = date.today()

    if fetch_start_date > end_date:
        return pd.DataFrame(columns=existing_df.columns)

    completed_games = fetch_completed_regular_season_games(fetch_start_date, end_date=end_date)
    new_rows = _build_rows_from_completed_games(existing_df, completed_games)
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
