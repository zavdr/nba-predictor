const API_BASE_URL = "http://127.0.0.1:8080";

let elements = {};

function init() {
  elements = {
    form: document.getElementById("prediction-form"),
    homeTeam: document.getElementById("home-team"),
    awayTeam: document.getElementById("away-team"),
    gameDate: document.getElementById("game-date"),
    predictButton: document.getElementById("predict-btn"),
    statusMessage: document.getElementById("status-message"),
    results: document.getElementById("results"),
    winnerName: document.getElementById("winner-name"),
    homeProbability: document.getElementById("home-probability"),
    awayProbability: document.getElementById("away-probability"),
    explanationText: document.getElementById("explanation-text"),
  };

  elements.form.addEventListener("submit", handleSubmit);
  loadTeams();
}

async function loadTeams() {
  setStatus("Loading teams...");

  try {
    const response = await fetch(`${API_BASE_URL}/teams`);
    const data = await response.json();

    if (!response.ok || !Array.isArray(data.teams)) {
      throw new Error("Could not load teams from the backend.");
    }

    populateSelect(elements.homeTeam, data.teams);
    populateSelect(elements.awayTeam, data.teams);
    setStatus("Teams loaded. Pick a matchup to get started.", "success");
  } catch (error) {
    setStatus(error.message || "Unable to load teams right now.", "error");
  }
}

function populateSelect(selectElement, teams) {
  selectElement.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Select a team";
  selectElement.appendChild(placeholder);

  teams.forEach((team) => {
    const option = document.createElement("option");
    option.value = team;
    option.textContent = team;
    selectElement.appendChild(option);
  });
}

async function handleSubmit(event) {
  event.preventDefault();

  const payload = {
    home_team: elements.homeTeam.value,
    away_team: elements.awayTeam.value,
    game_date: elements.gameDate.value,
  };

  if (!payload.home_team || !payload.away_team || !payload.game_date) {
    setStatus("Choose both teams and a game date before predicting.", "error");
    return;
  }

  if (payload.home_team === payload.away_team) {
    setStatus("Home and away teams must be different.", "error");
    return;
  }

  elements.predictButton.disabled = true;
  elements.predictButton.textContent = "Predicting...";
  setStatus("Running prediction...");

  try {
    const result = await fetchPrediction(payload);
    renderResults(result);
    setStatus("Prediction ready.", "success");
  } catch (error) {
    elements.results.hidden = true;
    setStatus(error.message || "Prediction failed.", "error");
  } finally {
    elements.predictButton.disabled = false;
    elements.predictButton.textContent = "Predict Game";
  }
}

async function fetchPrediction(payload) {
  const response = await fetch(`${API_BASE_URL}/predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "The backend could not generate a prediction.");
  }

  return data;
}

function renderResults(data) {
  elements.winnerName.textContent = data.predicted_winner;
  elements.homeProbability.textContent = `${data.home_team}: ${data.home_win_probability}%`;
  elements.awayProbability.textContent = `${data.away_team}: ${data.away_win_probability}%`;
  elements.explanationText.textContent = data.explanation;
  elements.results.hidden = false;
}

function setStatus(message, type = "") {
  elements.statusMessage.textContent = message;
  elements.statusMessage.className = "status-message";

  if (type === "error") {
    elements.statusMessage.classList.add("is-error");
  }

  if (type === "success") {
    elements.statusMessage.classList.add("is-success");
  }
}

document.addEventListener("DOMContentLoaded", init);
