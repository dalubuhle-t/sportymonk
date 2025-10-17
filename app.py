from flask import Flask, jsonify, request
import requests, os
from datetime import date
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

SPORTMONKS_API_KEY = os.getenv("SPORTMONKS_API_KEY")
BASE_URL = "https://api.sportmonks.com/v3/football"

def sportmonks_get(endpoint, params=None):
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

# --- UFP Prediction Engine (simplified) ---
def ufp_predict(team_a_data, team_b_data):
    """
    Generates simplified predictions for a match based on form and stats.
    """
    # Example logic: Home/away form, attack/defense stats
    # You can replace this with your full 24-layer UFP system
    a_attack = team_a_data.get("stats", {}).get("goals_scored", 1)
    a_defense = team_a_data.get("stats", {}).get("goals_conceded", 1)
    b_attack = team_b_data.get("stats", {}).get("goals_scored", 1)
    b_defense = team_b_data.get("stats", {}).get("goals_conceded", 1)
    
    # Simplified expected goals
    team_a_xg = (a_attack + b_defense) / 2
    team_b_xg = (b_attack + a_defense) / 2

    # Probabilities for 1X2 (simple normalized)
    total = team_a_xg + team_b_xg
    p1 = round(team_a_xg / total, 2)
    p2 = round(team_b_xg / total, 2)
    draw = round(1 - (p1 + p2), 2)
    
    # BTTS and Over/Under 2.5
    btts = team_a_xg > 0.8 and team_b_xg > 0.8
    over25 = (team_a_xg + team_b_xg) > 2.5

    # Most likely correct score (simplified)
    a_goals = round(team_a_xg)
    b_goals = round(team_b_xg)
    
    return {
        "1X2": {"home_win": p1, "draw": draw, "away_win": p2},
        "BTTS": btts,
        "Over2.5": over25,
        "Correct_Score": f"{a_goals}-{b_goals}"
    }

# --- UFP Endpoint ---
@app.route("/ufp/<team_a>/<team_b>")
def ufp_endpoint(team_a, team_b):
    # Fetch team info
    search_a = sportmonks_get("teams/search", {"name": team_a})
    search_b = sportmonks_get("teams/search", {"name": team_b})

    if not search_a.get("data") or not search_b.get("data"):
        return jsonify({"error": "One or both teams not found"}), 404

    team_a_id = search_a["data"][0]["id"]
    team_b_id = search_b["data"][0]["id"]

    team_a_data = sportmonks_get(f"teams/{team_a_id}", {"include": "stats,form,injuries"}).get("data", {})
    team_b_data = sportmonks_get(f"teams/{team_b_id}", {"include": "stats,form,injuries"}).get("data", {})

    # Generate prediction
    prediction = ufp_predict(team_a_data, team_b_data)

    return jsonify({
        "match": f"{team_a} vs {team_b}",
        "team_a": team_a_data,
        "team_b": team_b_data,
        "prediction": prediction
    })

# --- Home & routes ---
@app.route("/")
def home():
    return jsonify({"status": "SportMonks + UFP Predictions Live ✅"})

@app.route("/routes")
def list_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote(f"{rule.endpoint}: {methods} {rule}")
        output.append(line)
    return jsonify({"available_routes": output})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
