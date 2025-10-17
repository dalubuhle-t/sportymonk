from flask import Flask, jsonify, request
import requests, os
from datetime import date
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

SPORTMONKS_API_KEY = os.getenv("SPORTMONKS_API_KEY")
BASE_URL = "https://api.sportmonks.com/v3/football"


def sportmonks_get(endpoint, params=None):
    """Generic GET helper with API key injection and error handling"""
    if params is None:
        params = {}
    params["api_token"] = SPORTMONKS_API_KEY
    url = f"{BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "endpoint": endpoint}


# --- LEAGUE ENDPOINTS ---
@app.route("/football/leagues")
def leagues_all():
    data = sportmonks_get("leagues")
    return jsonify({"endpoint": "/football/leagues", "data": data})


@app.route("/football/leagues/<int:league_id>")
def league_details(league_id):
    data = sportmonks_get(f"leagues/{league_id}", {"include": "country,seasons"})
    return jsonify({"endpoint": f"/football/leagues/{league_id}", "data": data})


@app.route("/football/leagues/live")
def leagues_live():
    data = sportmonks_get("leagues/live")
    return jsonify({"endpoint": "/football/leagues/live", "data": data})


@app.route("/football/leagues/date/<string:date_str>")
def leagues_by_date(date_str):
    data = sportmonks_get(f"leagues/date/{date_str}")
    return jsonify({"endpoint": f"/football/leagues/date/{date_str}", "data": data})


@app.route("/football/leagues/countries/<int:country_id>")
def leagues_by_country(country_id):
    data = sportmonks_get(f"countries/{country_id}/leagues")
    return jsonify({"endpoint": f"/football/leagues/countries/{country_id}", "data": data})


@app.route("/football/leagues/search/<string:search_query>")
def leagues_search(search_query):
    data = sportmonks_get("leagues/search", {"name": search_query})
    return jsonify({"endpoint": f"/football/leagues/search/{search_query}", "data": data})


@app.route("/football/leagues/teams/<int:league_id>")
def league_teams(league_id):
    data = sportmonks_get(f"leagues/{league_id}/teams", {"include": "country"})
    return jsonify({"endpoint": f"/football/leagues/teams/{league_id}", "data": data})


@app.route("/football/leagues/teams/<int:league_id>/current")
def league_teams_current(league_id):
    data = sportmonks_get(f"leagues/{league_id}/teams/current")
    return jsonify({"endpoint": f"/football/leagues/teams/{league_id}/current", "data": data})


# --- Additional Endpoints ---
@app.route("/football/livescore/inplay")
def livescore_inplay():
    data = sportmonks_get("livescore/inplay")
    return jsonify({"endpoint": "/football/livescore/inplay", "data": data})


@app.route("/football/expected/fixtures")
def expected_fixtures():
    data = sportmonks_get("expected/fixtures")
    return jsonify({"endpoint": "/football/expected/fixtures", "data": data})


# --- UFP Prediction Endpoint ---
def ufp_predict(team_a_data, team_b_data):
    a_attack = team
