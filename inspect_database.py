"""
inspect_database.py
--------------------
A beginner-friendly way to LOOK INSIDE routes.db without installing
any extra tools. It just prints out what's in each table.

HOW TO RUN:
    python inspect_database.py

WHAT YOU SHOULD SEE:
    A printed list of all routes, their timetables, and any
    observations currently stored in the database.
"""

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FOLDER = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_FOLDER, "routes.db")


def inspect_database():
    if not os.path.exists(DATABASE_PATH):
        print(f"No database found at {DATABASE_PATH}")
        print("Run create_database.py and seed_database.py first.")
        return

    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    print("=" * 60)
    print("ROUTES")
    print("=" * 60)
    cursor.execute("SELECT route_id, source, destination, vehicle_type, route_name FROM routes")
    routes = cursor.fetchall()
    for row in routes:
        print(f"  [{row[0]}] {row[1]} -> {row[2]}  ({row[3]}, {row[4]})")
    print(f"Total routes: {len(routes)}")

    print()
    print("=" * 60)
    print("TIMETABLE")
    print("=" * 60)
    cursor.execute("""
        SELECT timetable.route_id, routes.source, routes.destination, timetable.departure_time
        FROM timetable
        JOIN routes ON timetable.route_id = routes.route_id
        ORDER BY timetable.route_id, timetable.departure_time
    """)
    timetable_rows = cursor.fetchall()
    for row in timetable_rows:
        print(f"  Route {row[0]} ({row[1]} -> {row[2]}): departs {row[3]}")
    print(f"Total timetable entries: {len(timetable_rows)}")

    print()
    print("=" * 60)
    print("OBSERVATIONS")
    print("=" * 60)
    cursor.execute("""
        SELECT observations.observation_id, routes.source, routes.destination,
               observations.observed_time, observations.delay_minutes, observations.submitted_at
        FROM observations
        JOIN routes ON observations.route_id = routes.route_id
        ORDER BY observations.observation_id
    """)
    observation_rows = cursor.fetchall()
    for row in observation_rows:
        print(f"  [{row[0]}] {row[1]} -> {row[2]}: observed {row[3]}, "
              f"delay {row[4]} min, submitted {row[5]}")
    print(f"Total observations: {len(observation_rows)}")

    connection.close()


if __name__ == "__main__":
    inspect_database()
