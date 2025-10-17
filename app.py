from flask import Flask, jsonify
import requests
import os
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


@app.route("/")
def home():
    return jsonify({"status": "SportMonks Connector + UFP Live ✅"})


@app.route("/fixtures/today")
def fixtures_today():
    today = date.today().strftime("%Y-%m-%d")
    data = sportmonks_get(f"fixtures/date/{today}", {"include": "localTeam,visitorTeam,league"})
    return jsonify({"date": today, "fixtures": data})


@app.route("/fixtures/live")
def fixtures_live():
    data = sportmonks_get("fixtures/live", {"include": "localTeam,visitorTeam,league"})
    return jsonify({"fixtures_live": data})


@app.route("/team/<int:team_id>")
def team_info(team_id):
    data = sportmonks_get(f"teams/{team_id}", {"include": "squad,stats,form"})
    return jsonify({"team_id": team_id, "data": data})


@app.route("/player/<int:player_id>")
def player_info(player_id):
    data = sportmonks_get(f"players/{player_id}", {"include": "stats,team"})
    return jsonify({"player_id": player_id, "data": data})


@app.route("/standings/<int:league_id>")
def standings(league_id):
    data = sportmonks_get(f"standings/seasons/{league_id}", {"include": "standings.participants"})
    return jsonify({"league_id": league_id, "standings": data})


@app.route("/ufp/<team_a>/<team_b>")
def ufp_prediction_data(team_a, team_b):
    """
    Provides normalized input for UFP System — form, goals, injuries
    """
    try:
        # 1. Search both teams
        search_a = sportmonks_get("teams/search", {"name": team_a})
        search_b = sportmonks_get("teams/search", {"name": team_b})

        if "data" not in search_a or "data" not in search_b or not search_a["data"] or not search_b["data"]:
            return jsonify({"error": "One or both teams not found", "team_a": team_a, "team_b": team_b}), 404

        team_a_id = search_a["data"][0]["id"]
        team_b_id = search_b["data"][0]["id"]

        # 2. Fetch stats and form
        a_info = sportmonks_get(f"teams/{team_a_id}", {"include": "stats,form,injuries"})
        b_info = sportmonks_get(f"teams/{team_b_id}", {"include": "stats,form,injuries"})

        # 3. Simplify for UFP
        result = {
            "match": f"{team_a} vs {team_b}",
            "team_a": {
                "id": team_a_id,
                "name": team_a,
                "recent_form": a_info.get("data", {}).get("form", []),
                "stats": a_info.get("data", {}).get("stats", {}),
                "injuries": a_info.get("data", {}).get("injuries", []),
            },
            "team_b": {
                "id": team_b_id,
                "name": team_b,
                "recent_form": b_info.get("data", {}).get("form", []),
                "stats": b_info.get("data", {}).get("stats", {}),
                "injuries": b_info.get("data", {}).get("injuries", []),
            },
        }
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
