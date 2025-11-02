from flask import Flask, jsonify, request
from flask_cors import CORS
import requests, os
from datetime import date
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow ChatGPT, browsers, etc.

# --- Configuration ---
SPORTMONKS_API_KEY = os.getenv("SPORTMONKS_API_KEY")
BASE_URL = "https://api.sportmonks.com/v3/football"

# --- In-memory caches for live updates via webhook ---
live_matches_cache = []
player_stats_cache = []

# --- Helper: API Request Wrapper ---
def sportmonks_get(endpoint, params=None):
    """Generic GET helper with API key injection and safe error handling"""
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

# --- FOOTBALL ENDPOINTS (unchanged) ---
@app.route("/football/leagues")
def leagues_all():
    data = sportmonks_get("leagues")
    return jsonify({"endpoint": "/football/leagues", "data": data}), 200

@app.route("/football/leagues/<int:league_id>")
def league_details(league_id):
    data = sportmonks_get(f"leagues/{league_id}", {"include": "country,seasons"})
    return jsonify({"endpoint": f"/football/leagues/{league_id}", "data": data}), 200

@app.route("/football/livescore/inplay")
def livescore_inplay():
    data = sportmonks_get("livescores/inplay", {"include": "league,localTeam,visitorTeam"})
    return jsonify({"endpoint": "/football/livescore/inplay", "data": data}), 200

@app.route("/football/expected/fixtures")
def expected_fixtures():
    data = sportmonks_get("fixtures/expected", {"include": "league,localTeam,visitorTeam"})
    return jsonify({"endpoint": "/football/expected/fixtures", "data": data}), 200

# --- UFP Prediction Model (unchanged) ---
def ufp_predict(team_a_data, team_b_data):
    a_attack = team_a_data.get("stats", {}).get("goals_scored", 1)
    a_defense = team_a_data.get("stats", {}).get("goals_conceded", 1)
    b_attack = team_b_data.get("stats", {}).get("goals_scored", 1)
    b_defense = team_b_data.get("stats", {}).get("goals_conceded", 1)

    team_a_xg = (a_attack + b_defense) / 2
    team_b_xg = (b_attack + a_defense) / 2

    total = team_a_xg + team_b_xg
    p1 = round(team_a_xg / total, 2)
    p2 = round(team_b_xg / total, 2)
    draw = round(1 - (p1 + p2), 2)

    btts = team_a_xg > 0.8 and team_b_xg > 0.8
    over25 = (team_a_xg + team_b_xg) > 2.5
    a_goals = round(team_a_xg)
    b_goals = round(team_b_xg)

    return {
        "1X2": {"home_win": p1, "draw": draw, "away_win": p2},
        "BTTS": btts,
        "Over2.5": over25,
        "Correct_Score": f"{a_goals}-{b_goals}"
    }

@app.route("/ufp/<team_a>/<team_b>")
def ufp_endpoint(team_a, team_b):
    search_a = sportmonks_get("teams/search", {"name": team_a})
    search_b = sportmonks_get("teams/search", {"name": team_b})

    if not search_a.get("data") or not search_b.get("data"):
        return jsonify({"error": "One or both teams not found"}), 404

    team_a_id = search_a["data"][0]["id"]
    team_b_id = search_b["data"][0]["id"]

    team_a_data = sportmonks_get(f"teams/{team_a_id}", {"include": "stats,form,injuries"}).get("data", {})
    team_b_data = sportmonks_get(f"teams/{team_b_id}", {"include": "stats,form,injuries"}).get("data", {})

    prediction = ufp_predict(team_a_data, team_b_data)
    return jsonify({
        "match": f"{team_a} vs {team_b}",
        "team_a": team_a_data,
        "team_b": team_b_data,
        "prediction": prediction
    }), 200

# --- WEBHOOK ENDPOINTS ---
@app.route("/webhook/live-match", methods=["POST"])
def webhook_live_match():
    """Receive real-time match updates from external services"""
    data = request.json
    match_id = data.get("matchId")
    if match_id:
        existing = next((m for m in live_matches_cache if m["matchId"] == match_id), None)
        if existing:
            existing.update(data)
        else:
            live_matches_cache.append(data)
    return jsonify({"status": "received"}), 200

@app.route("/matches", methods=["GET"])
def get_live_matches():
    """Expose live matches to ChatGPT via GET"""
    league = request.args.get("league")
    matches = [m for m in live_matches_cache if not league or m.get("league") == league]
    return jsonify({"matches": matches}), 200

@app.route("/webhook/player-stats", methods=["POST"])
def webhook_player_stats():
    """Receive real-time player stats updates"""
    data = request.json
    player_id = data.get("playerId")
    if player_id:
        existing = next((p for p in player_stats_cache if p["playerId"] == player_id), None)
        if existing:
            existing.update(data)
        else:
            player_stats_cache.append(data)
    return jsonify({"status": "received"}), 200

@app.route("/player-stats", methods=["GET"])
def get_player_stats():
    """Expose player stats to ChatGPT via GET"""
    return jsonify({"playerStats": player_stats_cache}), 200

# --- Home & Routes ---
@app.route("/")
def home():
    return jsonify({"status": "✅ SportMonks + UFP Extended API with Webhooks Live & ChatGPT-Compatible"}), 200

@app.route("/routes")
def list_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote(f"{rule.endpoint}: {methods} {rule}")
        output.append(line)
    return jsonify({"available_routes": output}), 200

# --- Run ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
