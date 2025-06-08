from flask import Flask, render_template, jsonify, request

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import dashboard.web_utils as web_utils
from log_utils.logger_util import get_logger
import logging
from data import DB

app = Flask(__name__)
flask_logger = get_logger("flask_app", "flask_app.log")

db_obj = DB()

flask_logger = get_logger("flask_app", "flask_app.log")
# --- 1. Replace Flask's logger ---
app.logger.handlers = []  # Remove default Flask handlers
app.logger.propagate = False
app.logger.setLevel(flask_logger.level)
for handler in flask_logger.handlers:
    app.logger.addHandler(handler)

# --- 2. Replace Werkzeug logger ---
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.handlers = []  # Remove default terminal handler
werkzeug_logger.propagate = False
werkzeug_logger.setLevel(flask_logger.level)
for handler in flask_logger.handlers:
    werkzeug_logger.addHandler(handler)


@app.route("/")
def index():
    timings = db_obj.get_timing_today()
    timings_for_display = []

    # Format the timings for display.
    # timing.exe_name, timing.date, timing.duration
    for timing in timings:
        formatted_timing = {
            "exe_name": timing[0],
            "date": timing[2],
            "duration": web_utils.convert_seconds_to_human_readable(
                timing[1]
            ),  # Format for display
        }
        timings_for_display.append(formatted_timing)

    todays_timings = db_obj.get_total_time_today() or 0
    todays_timings_str = web_utils.convert_seconds_to_human_readable_extended(
        todays_timings
    )

    # Get all violations
    violations = db_obj.get_all_violations()
    violations_by_exe = {}
    if len(violations) > 0:
        # Group by exe_name
        for violation in violations:
            exe_name = violation[0]
            if exe_name not in violations_by_exe:
                violations_by_exe[exe_name] = []
            violations_by_exe[exe_name].append(
                {
                    "timestamp": violation[1],
                    "reason": violation[2],
                }
            )

    return render_template(
        "index.html",
        timings=timings_for_display,
        todays_timings=todays_timings,
        todays_timings_str=todays_timings_str,
        formatted_violations=violations_by_exe,
    )


@app.route("/settings")
def settings():
    # Get all exes and their classifications
    all_exes = db_obj.get_all_processes()
    apps = []
    for exe in all_exes:
        exe_info = {
            "name": exe[0],
            "is_game": bool(exe[1]),
            "user_marked": bool(exe[2]),
        }
        apps.append(exe_info)
    # Sort apps to show games first
    apps.sort(key=lambda x: (not x["is_game"], x["name"].lower()))

    # Get all time based settings
    time_limits = db_obj.get_all_timing_settings()
    time_limit_settings = []
    for setting in time_limits:
        setting_info = {
            "exe_name": setting[0],
            "max_time": setting[1],
            "notify_limit": setting[2],
        }
        time_limit_settings.append(setting_info)

    global_timing_limit = db_obj.get_global_timing_limit()

    return render_template(
        "settings.html",
        apps=apps,
        time_limit_settings=time_limit_settings,
        global_timing_limit=global_timing_limit,
    )


@app.route("/api/update_exe_classification", methods=["POST"])
def update_exe_classification():
    """
    API endpoint to update the classification of an executable.
    Expects a JSON payload with 'exe_name', 'is_game', and 'user_marked' keys.
    """
    if not request.is_json:
        return jsonify({"error": "Expected JSON. You sent something else."}), 400

    data = request.get_json()
    if "exe_name" not in data or "is_game" not in data:
        return jsonify({"error": "Missing required fields in request body."}), 400
    print(data)
    exe_name = data["exe_name"]
    is_game = bool(data["is_game"])
    user_marked = 1  # If user is updating, we assume they are marking it themselves

    db_obj.upsert_is_game(exe_name, is_game, user_marked)

    return jsonify(
        {"status": "success", "message": f"Updated classification for {exe_name}."}
    )


@app.route("/api/are_games_running", methods=["POST"])
def are_games_running():
    """
    API endpoint to check if given games are running.
    Returns a JSON response with the list of running games.
    """
    if not request.is_json:
        return jsonify({"error": "Invalid request format"}), 400

    data = request.get_json()
    if "games" not in data:
        return jsonify({"error": "No games provided"}), 400

    games = data["games"]
    if not isinstance(games, list):
        return jsonify({"error": "Games should be a list"}), 400

    running_games = web_utils.check_if_processes_running(exe_names=games)

    return jsonify({"running_games": running_games})


@app.route("/api/update_global_timing", methods=["POST"])
def update_global_timing():
    """
    API endpoint to update the global timing limit.
    Expects a JSON payload with a 'limit' key (in minutes).
    """
    if not request.is_json:
        return jsonify({"error": "Expected JSON. You sent something else."}), 400

    data = request.get_json()
    if "limit" not in data:
        return (
            jsonify({"error": 'Missing "limit" in request body. Try again, champ.'}),
            400,
        )

    limit = data["limit"]

    if not isinstance(limit, int) or limit < 0:
        return (
            jsonify({"error": "Limit must be a non-negative integer. Nice try."}),
            400,
        )

    if limit > 180:  # Max 3 hours
        return jsonify({"error": "180 minutes is the max. Go touch some grass 🌱"}), 400

    db_obj.update_global_timing_settings(limit)

    return jsonify(
        {
            "status": "success",
            "message": f"Global timing limit updated to {limit} minutes. Don’t make us regret this.",
        }
    )


@app.route("/api/refresh_time_limit_list", methods=["POST"])
def refresh_time_limit_list():
    """
    API endpoint to refresh the timing list.
    This will set defaults for all exes that are classified as games but don't have specific timing settings.
    Return status and message.
    """
    try:
        db_obj.refresh_time_limit_list()
        return jsonify(
            {
                "status": "success",
                "message": "Timing list refreshed. Defaults set for all games without specific limits.",
            }
        )
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Failed to refresh timing list: {str(e)}",
                }
            ),
            500,
        )


@app.route("/api/update_time_limit", methods=["POST"])
def update_time_limit():
    """
    API endpoint to update the time limit for a specific game.
    Expects a JSON payload with 'exe_name', 'max_time', and 'notify_limit'(ignored).
    """
    if not request.is_json:
        return jsonify({"error": "Expected JSON. You sent something else."}), 400

    data = request.get_json()
    if "exe_name" not in data or "max_time" not in data:
        return jsonify({"error": "Missing required fields in request body."}), 400

    exe_name = data["exe_name"]
    max_time = int(data["max_time"])

    if max_time < 0:
        return (
            jsonify({"error": "Time limits must be non-negative integers. Nice try."}),
            400,
        )

    if max_time > 180:  # Max 3 hours
        return jsonify({"error": "180 minutes is the max. Go touch some grass 🌱"}), 400

    db_obj.update_timing_settings(exe_name, max_time)

    return jsonify(
        {
            "status": "success",
            "message": f"Time limit for {exe_name} updated successfully.",
        }
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
