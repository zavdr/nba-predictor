/**
 * Handles form submission, calls the Flask API (e.g. /predict), and renders
 * predicted winner, win probability, and natural-language explanation in the DOM.
 */

function init() {
  // Wire predict button, optional team list fetch, and results panel updates.
}

function fetchPrediction(payload) {
  // POST JSON { home_team, away_team, game_date } to backend; render response.
}

function renderResults(data) {
  // Populate #results with winner, probability, explanation; show #results.
}

document.addEventListener("DOMContentLoaded", init);
