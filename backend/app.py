from agent import run_agent
from stats import get_all_teams
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()


app = Flask(__name__)
CORS(app)


@app.route('/teams', methods=['GET'])
def teams():
    return jsonify({'teams': get_all_teams()})


@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()

    home_team = data.get('home_team', '').upper().strip()
    away_team = data.get('away_team', '').upper().strip()
    game_date = data.get('game_date', '')

    if not home_team or not away_team or not game_date:
        return jsonify({'error': 'home_team, away_team, and game_date are required'}), 400

    if home_team == away_team:
        return jsonify({'error': 'Home and away teams must be different'}), 400

    result = run_agent(home_team, away_team, game_date)

    if 'error' in result:
        return jsonify(result), 500

    return jsonify(result)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
