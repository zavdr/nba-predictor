import anthropic
import json
import os
from stats import get_team_stats
from predictor import predict

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

TOOLS = [
    {
        'name': 'get_team_stats',
        'description': 'Get pregame statistics for an NBA team before a given date. Returns win percentage, last 5 game win rate, average points, and rest days.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'team': {
                    'type': 'string',
                    'description': 'NBA team abbreviation e.g. LAL, BOS, GSW'
                },
                'date': {
                    'type': 'string',
                    'description': 'Game date in YYYY-MM-DD format'
                }
            },
            'required': ['team', 'date']
        }
    },
    {
        'name': 'predict_game',
        'description': 'Run the ML model to predict the winner of a game given home and away team stats.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'home_stats': {
                    'type': 'object',
                    'description': 'Stats dict for the home team from get_team_stats'
                },
                'away_stats': {
                    'type': 'object',
                    'description': 'Stats dict for the away team from get_team_stats'
                }
            },
            'required': ['home_stats', 'away_stats']
        }
    }
]


def run_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == 'get_team_stats':
        result = get_team_stats(tool_input['team'], tool_input['date'])
        return json.dumps(result)
    elif tool_name == 'predict_game':
        result = predict(tool_input['home_stats'], tool_input['away_stats'])
        return json.dumps(result)
    return json.dumps({'error': f'Unknown tool: {tool_name}'})


def run_agent(home_team: str, away_team: str, game_date: str) -> dict:
    messages = [
        {
            'role': 'user',
            'content': (
                f'Predict the NBA game: {home_team} (home) vs {away_team} (away) on {game_date}. '
                f'Use the tools to: 1) get stats for both teams, 2) run the prediction model, '
                f'3) return a JSON response with these exact keys: '
                f'"predicted_winner", "home_win_probability", "away_win_probability", '
                f'"home_team", "away_team", "explanation". '
                f'The explanation should be 2-3 sentences in plain English describing '
                f'why the predicted team is favored, referencing the actual stat values.'
            )
        }
    ]

    while True:
        response = client.messages.create(
            model='claude-sonnet-4-20250514',
            max_tokens=1000,
            tools=TOOLS,
            messages=messages
        )

        if response.stop_reason == 'tool_use':
            tool_results = []
            for block in response.content:
                if block.type == 'tool_use':
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        'type':        'tool_result',
                        'tool_use_id': block.id,
                        'content':     result
                    })

            messages.append({'role': 'assistant', 'content': response.content})
            messages.append({'role': 'user',      'content': tool_results})

        elif response.stop_reason == 'end_turn':
            for block in response.content:
                if hasattr(block, 'text'):
                    text = block.text.strip()
                    if text.startswith('{'):
                        return json.loads(text)
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    if start != -1 and end != 0:
                        return json.loads(text[start:end])
            break

    return {'error': 'Agent did not return a valid prediction'}
