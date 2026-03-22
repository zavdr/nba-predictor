"""
Flask application for the NBA predictor API.

Will expose HTTP routes (e.g. POST /predict and POST /explain) that accept home team,
away team, and game date, delegate to stats lookup and the Claude agent, and return
JSON for the frontend. May later serve the frontend/ folder as static files or enable CORS.
"""
from flask import Flask

app = Flask(__name__)


@app.route("/predict", methods=["POST"])
def predict():
    """Receive prediction request; look up stats, run agent + model; return structured result."""
    pass


@app.route("/explain", methods=["POST"])
def explain():
    """Optional route for explanation-only flow, or alias to full prediction + narrative."""
    pass


if __name__ == "__main__":
    # Development server entry point (implementation later).
    pass
