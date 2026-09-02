"""
RaahSetu - Backend (Member 1: Backend Lead)
=============================================
Flask + SQLite backend for the RaahSetu MVP.
Responsibilities covered in this file:
1. Flask app setup
2. SQLite connection handling
3. Search API -> GET /search
4. Observation API -> POST /submit-observation
5. Next-departure logic -> get_next_departure()
INTEGRATION CONTRACT (read this before wiring up frontend / database)
-----------------------------------------------------------------------
Member 2 (Frontend) should call:
GET /search?source=<text>&destination=<text>
POST /submit-observation with JSON body {route_id, delay_minutes, note}
GET /routes/options (bonus helper for building dropdowns/autocomplete)
The database scripts create SQLite data at database/routes.db using
routes, timetable, and observations tables. The app initializes or upgrades
that database automatically through create_database.py.
Every JSON response follows the same envelope so the frontend can handle
all responses the same way:
{ "status": "success" | "error", "message": "...", ...extra data }
"""
import os
import sqlite3
from datetime import datetime, timedelta

from create_database import create_database
from flask import Flask, render_template, request, jsonify, g


# ----------------------------------------------------------------------
# 1. APP + CONFIG
# ----------------------------------------------------------------------
app = Flask(
    __name__,
    template_folder=os.path.join("RaahSetu", "templates"),
    static_folder=os.path.join("RaahSetu", "static"),
)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "routes.db")


# If Member 2's frontend is opened as a static file (e.g. VS Code Live
# Server on a different port) instead of served by Flask, uncomment the
# two lines below after running: pip install flask-cors
#
# from flask_cors import CORS
# CORS(app)
# ----------------------------------------------------------------------
# 2. DATABASE CONNECTION HANDLING
# ----------------------------------------------------------------------
def get_db():
    """Opens a new database connection per request (Flask's recommended
    pattern using the 'g' object) so every route reuses the same
    connection instead of opening a fresh one each time.
    """
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row  # lets us access columns by name
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """Automatically closes the DB connection when the request ends."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """
    Creates the required tables if they don't already exist.
    Safe to run every time the app starts -- CREATE TABLE IF NOT EXISTS
    never touches existing data. This means Member 1 can start building
    immediately without waiting on Member 3, and it won't ever wipe the
    real dataset once Member 3 loads it in.
    """
    create_database()


# ----------------------------------------------------------------------
# 3. NEXT-DEPARTURE LOGIC (core MVP feature)
# ----------------------------------------------------------------------
def get_next_departure(first_departure, last_departure, frequency_minutes, now=None):
    """
    Works out the next expected departure window for a route.
    Args:
        first_departure (str): 'HH:MM' - first vehicle of the day
        last_departure (str): 'HH:MM' - last vehicle of the day
        frequency_minutes (int): how often a vehicle runs
        now (datetime): injectable for testing; defaults to current time
    Returns:
        dict: next departure and service status.
    """
    now = now or datetime.now()
    today = now.date()
    first_dt = datetime.combine(
        today, datetime.strptime(first_departure, "%H:%M").time()
    )
    last_dt = datetime.combine(
        today, datetime.strptime(last_departure, "%H:%M").time()
    )

    # Service hasn't started yet today.
    if now < first_dt:
        return {
            "next_departure": first_dt.strftime("%H:%M"),
            "service_status": "upcoming",
        }

    # Service has finished for today -> show tomorrow's first departure.
    if now > last_dt:
        next_day = first_dt + timedelta(days=1)
        return {
            "next_departure": next_day.strftime("%H:%M"),
            "service_status": "ended_for_today",
        }

    # Currently within service hours -> find the next slot from frequency.
    elapsed_minutes = (now - first_dt).total_seconds() / 60
    slots_passed = elapsed_minutes // frequency_minutes
    next_dt = first_dt + timedelta(minutes=(slots_passed + 1) * frequency_minutes)
    if next_dt > last_dt:
        next_day = first_dt + timedelta(days=1)
        return {
            "next_departure": next_day.strftime("%H:%M"),
            "service_status": "ended_for_today",
        }

    return {
        "next_departure": next_dt.strftime("%H:%M"),
        "service_status": "running",
    }


def get_next_scheduled_departure(departure_times, now=None):
    """Return the next departure from a route's timetable entries."""
    now = now or datetime.now()
    today = now.date()
    departures = sorted(
        datetime.combine(today, datetime.strptime(time, "%H:%M").time())
        for time in departure_times
    )
    if not departures:
        return {"next_departure": None, "service_status": "no_schedule"}

    for departure in departures:
        if departure > now:
            return {
                "next_departure": departure.strftime("%H:%M"),
                "service_status": (
                    "upcoming" if now < departures[0] else "running"
                ),
            }

    return {
        "next_departure": departures[0].strftime("%H:%M"),
        "service_status": "ended_for_today",
    }


# ----------------------------------------------------------------------
# 4. ROUTES / VIEWS
# ----------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/search")
def search():
    """
    GET /search?source=<text>&destination=<text>
    Both params are required. Matching is case-insensitive and allows
    partial text (so 'station' matches 'Railway Station').
    Success response:
    {
    "status": "success",
    "count": 2,
    "routes": [
    {
    "id": 1,
    "route_name": "Railway Station - College",
    "source": "Railway Station",
    "destination": "College",
    "mode": "bus",
    "frequency_minutes": 20,
    "next_departure": "14:40",
    "service_status": "running"
    }
    ]
    }
    """
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    if not source or not destination:
        return jsonify(
            {
                "status": "error",
                "message": "Both 'source' and 'destination' query parameters are required.",
            }
        ), 400
    db = get_db()
    rows = db.execute(
        """
                SELECT route_id, route_name, source, destination, vehicle_type
        FROM routes
                WHERE source LIKE ? COLLATE NOCASE
                    AND destination LIKE ? COLLATE NOCASE
                ORDER BY route_name
        """,
        (f"%{source}%", f"%{destination}%"),
    ).fetchall()
    results = []
    for row in rows:
        timetable = db.execute(
            """
            SELECT departure_time
            FROM timetable
            WHERE route_id = ?
            ORDER BY departure_time
            """,
            (row["route_id"],),
        ).fetchall()
        departure_info = get_next_scheduled_departure(
            [entry["departure_time"] for entry in timetable]
        )
        timetable_times = [entry["departure_time"] for entry in timetable]
        results.append(
            {
                "id": row["route_id"],
                "route_id": row["route_id"],
                "route_name": row["route_name"],
                "source": row["source"],
                "destination": row["destination"],
                "mode": row["vehicle_type"],
                "vehicle_type": row["vehicle_type"],
                "timetable": timetable_times,
                "next_departure": departure_info["next_departure"],
                "service_status": departure_info["service_status"],
            }
        )

    return jsonify(
        {
            "status": "success",
            "count": len(results),
            "routes": results,
            "message": (
                None
                if results
                else "No routes found for this source/destination."
            ),
        }
    ), 200


@app.route("/submit-observation", methods=["POST"])
def submit_observation():
    """
POST /submit-observation
Body (JSON):
{
"route_id": 1,
"delay_minutes": 5,
"note": "Bus was crowded" // optional
}
Success response:
{ "status": "success", "message": "Observation recorded.", "observation_id": 7 }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify(
            {"status": "error", "message": "Request body must be JSON."}
        ), 400

    route_id = data.get("route_id")
    delay_minutes = data.get("delay_minutes")
    note = data.get("note", "")

    if route_id is None or delay_minutes is None:
        return jsonify(
            {
                "status": "error",
                "message": "'route_id' and 'delay_minutes' are required.",
            }
        ), 400

    if not isinstance(route_id, int) or not isinstance(delay_minutes, int):
        return jsonify(
            {
                "status": "error",
                "message": "'route_id' and 'delay_minutes' must be integers.",
            }
        ), 400

    db = get_db()
    route_exists = db.execute(
        "SELECT route_id FROM routes WHERE route_id = ?", (route_id,)
    ).fetchone()

    if not route_exists:
        return jsonify(
            {
                "status": "error",
                "message": f"No route found with id {route_id}.",
            }
        ), 404

    cursor = db.execute(
        """
        INSERT INTO observations
            (route_id, observed_time, delay_minutes, note, submitted_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            route_id,
            datetime.now().strftime("%H:%M"),
            delay_minutes,
            note,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    db.commit()
    return jsonify({
        "status": "success",
        "message": "Report submitted.",
        "observation_id": cursor.lastrowid,
    }), 201


@app.route("/observations")
def observations():
    """Return submitted observations, optionally filtered by route."""
    route_id = request.args.get("route_id", type=int)
    db = get_db()
    query = """
        SELECT observations.observation_id, observations.route_id,
               routes.route_name, routes.source, routes.destination,
               routes.vehicle_type, observations.observed_time,
               observations.delay_minutes, observations.note,
               observations.submitted_at
        FROM observations
        JOIN routes ON observations.route_id = routes.route_id
    """
    parameters = ()
    if route_id is not None:
        query += " WHERE observations.route_id = ?"
        parameters = (route_id,)
    query += " ORDER BY observations.observation_id DESC"

    rows = db.execute(query, parameters).fetchall()
    return jsonify(
        {
            "status": "success",
            "count": len(rows),
            "observations": [dict(row) for row in rows],
            "message": None if rows else "No observations found.",
        }
    ), 200


@app.route("/reports")
def reports_page():
    """Render submitted reports grouped by their reported delay."""
    db = get_db()
    rows = db.execute(
        """
        SELECT observations.observation_id, observations.route_id,
               routes.route_name, routes.source, routes.destination,
               routes.vehicle_type, observations.observed_time,
               observations.delay_minutes, observations.note,
               observations.submitted_at
        FROM observations
        JOIN routes ON observations.route_id = routes.route_id
        ORDER BY observations.delay_minutes DESC, observations.observation_id DESC
        """
    ).fetchall()

    report_counts = {}
    for row in rows:
        report_counts[row["route_id"]] = report_counts.get(row["route_id"], 0) + 1

    category_names = [
        ("On time", "0 minutes", lambda delay: delay == 0),
        ("Minor delay", "1-5 minutes", lambda delay: 1 <= delay <= 5),
        ("Moderate delay", "6-15 minutes", lambda delay: 6 <= delay <= 15),
        ("Severe delay", "16+ minutes", lambda delay: delay >= 16),
    ]
    categories = []
    for name, range_label, matches in category_names:
        reports = []
        for row in rows:
            if matches(row["delay_minutes"]):
                report = dict(row)
                report["report_count"] = report_counts[row["route_id"]]
                reports.append(report)
        categories.append(
            {"name": name, "range_label": range_label, "reports": reports}
        )

    return render_template(
        "reports.html",
        categories=categories,
        most_delayed=dict(rows[0]) if rows else None,
    )


@app.route("/routes/options")
def route_options():
    """
    BONUS endpoint for Member 2 (not required by the handbook, but makes
    the search form nicer). Returns every distinct source and destination
    currently in the database, e.g. for autocomplete dropdowns.
    { "status": "success", "sources": [...], "destinations": [...] }
    """
    db = get_db()
    sources = [
        r["source"]
        for r in db.execute("SELECT DISTINCT source FROM routes ORDER BY source")
    ]
    destinations = [
        r["destination"]
        for r in db.execute("SELECT DISTINCT destination FROM routes ORDER BY destination")
    ]
    return jsonify(
        {
            "status": "success",
            "sources": sources,
            "destinations": destinations,
        }
    ), 200


@app.route("/health")
def health():
    """Quick check used while developing -- confirms the server + DB are alive."""
    try:
        get_db().execute("SELECT 1")
        return jsonify(
            {
                "status": "success",
                "message": "API and database are reachable.",
            }
        ), 200
    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ----------------------------------------------------------------------
# 5. ERROR HANDLERS (so the frontend always gets JSON, never an HTML page)
# ----------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "message": "Endpoint not found."}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"status": "error", "message": "Internal server error."}), 500


# ----------------------------------------------------------------------
# 6. ENTRY POINT
# ----------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
