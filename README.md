# NBA Predictor

Web app skeleton: user picks home team, away team, and game date; the Flask backend loads pregame stats from `data/full_dataset.csv`, runs a Claude agent (Anthropic tool use / function calling) to assemble features and call the saved sklearn pipeline, then returns win probability and a natural-language explanation.

## Stack

- **Backend:** Python, Flask (`backend/app.py`)
- **AI:** Anthropic Claude API with tool use (`backend/agent.py`)
- **ML:** Pre-trained scikit-learn pipeline at `model/nba_model.pkl` (`backend/predictor.py`) — **do not retrain** in this repo; replace placeholder files with your trained artifacts
- **Optional:** `model/nba_features.pkl` for feature metadata if your training pipeline saved it
- **Frontend:** Single HTML/CSS/JS in `frontend/` — no build step, no React/TypeScript
- **Config:** `python-dotenv` reads `.env`

## Environment variables

Create `.env` (see `.gitignore` — do not commit real secrets):

- `ANTHROPIC_API_KEY` — Anthropic API key
- `FLASK_SECRET_KEY` — Flask session/signing secret

## Data and model files

- **Stats:** All team statistics must be looked up from `data/full_dataset.csv` via `backend/stats.py` — not hardcoded.
- **Model:** Place trained `nba_model.pkl` (and `nba_features.pkl` if used) under `model/`. The repository currently contains **empty placeholders** so paths exist; replace them with your real files before inference.

## Running (to be wired in implementation)

1. Create a virtual environment and install: `pip install -r requirements.txt`
2. Set `.env` variables
3. Run the Flask app from `backend/app.py` (exact command TBD)
4. Open `frontend/index.html` in a browser (or serve static files from Flask — TBD)

## Flow

1. Frontend sends home team, away team, and game date to the API.
2. Backend loads both teams’ pregame stats from the CSV.
3. Claude uses **tool calling** to assemble features and invoke the ML model.
4. Model returns win probability; Claude generates an explanation.
5. Frontend shows predicted winner, probability, and explanation.
