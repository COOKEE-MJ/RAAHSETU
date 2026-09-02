"""
seed_database.py
-----------------
Fills routes.db with sample RaahSetu data: routes, their timetables,
and a few example crowdsourced observations.

This script is SAFE TO RUN MULTIPLE TIMES. It first DELETES all
existing rows from the three tables, then re-inserts the sample data.
That means you can run it again anytime to "reset" the demo data
without ending up with duplicate rows.

IMPORTANT: Run create_database.py FIRST (only once is needed, but
running it again is harmless too). This script assumes the tables
already exist.

HOW TO RUN (from VS Code terminal, from anywhere inside the project):
    python database/seed_database.py

WHAT YOU SHOULD SEE:
    Cleared old data from routes, timetable, observations.
    Inserted 18 routes.
    Inserted 93 timetable entries.
    Inserted 5 sample observations.
    Seeding complete.
"""

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FOLDER = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_FOLDER, "routes.db")

# ---------------------------------------------------------------------
# SAMPLE DATA
# Each entry: (source, destination, vehicle_type, route_name, [times])
# Times are 24-hour "HH:MM" strings - simple and easy to compare.
# This is representative small-town/informal-transport style data:
# shared tempos, feeder buses, and short local routes.
# ---------------------------------------------------------------------
SAMPLE_ROUTES = [
    ("Railway Station", "Old Bus Stand", "Shared Tempo", "Tempo Route 1",
     ["06:00", "06:30", "07:00", "07:30", "08:00"]),
    ("Old Bus Stand", "Railway Station", "Shared Tempo", "Tempo Route 1 Return",
     ["06:15", "06:45", "07:15", "07:45", "08:15"]),
    ("Railway Station", "College Gate", "Feeder Bus", "Feeder Route A",
     ["07:00", "08:30", "10:00", "13:00", "17:00"]),
    ("College Gate", "Railway Station", "Feeder Bus", "Feeder Route A Return",
     ["07:45", "09:15", "10:45", "13:45", "17:45"]),
    ("Market Chowk", "Industrial Area", "Shared Tempo", "Tempo Route 2",
     ["06:30", "07:00", "07:30", "08:00", "08:30", "09:00"]),
    ("Industrial Area", "Market Chowk", "Shared Tempo", "Tempo Route 2 Return",
     ["17:00", "17:30", "18:00", "18:30", "19:00"]),
    ("Bus Depot", "Hill View Colony", "Local Bus", "City Bus 5",
     ["06:00", "08:00", "10:00", "12:00", "14:00", "16:00", "18:00"]),
    ("Hill View Colony", "Bus Depot", "Local Bus", "City Bus 5 Return",
     ["07:00", "09:00", "11:00", "13:00", "15:00", "17:00", "19:00"]),
    ("Railway Station", "Riverside Colony", "Shared Tempo", "Tempo Route 3",
     ["06:15", "06:45", "07:15", "07:45"]),
    ("Riverside Colony", "Railway Station", "Shared Tempo", "Tempo Route 3 Return",
     ["08:00", "08:30", "09:00", "09:30"]),
    ("Central Market", "University Road", "Feeder Bus", "Feeder Route B",
     ["07:15", "09:15", "11:15", "14:15", "16:15"]),
    ("University Road", "Central Market", "Feeder Bus", "Feeder Route B Return",
     ["08:00", "10:00", "12:00", "15:00", "17:00"]),
    ("Old Bus Stand", "Industrial Area", "Local Bus", "City Bus 7",
     ["06:30", "08:30", "10:30", "12:30", "14:30", "16:30"]),
    ("Industrial Area", "Old Bus Stand", "Local Bus", "City Bus 7 Return",
     ["07:30", "09:30", "11:30", "13:30", "15:30", "17:30"]),
    ("Market Chowk", "Hill View Colony", "Shared Tempo", "Tempo Route 4",
     ["06:00", "06:40", "07:20", "08:00"]),
    ("Hill View Colony", "Market Chowk", "Shared Tempo", "Tempo Route 4 Return",
     ["17:15", "17:55", "18:35", "19:15"]),
    ("Bus Depot", "Riverside Colony", "Feeder Bus", "Feeder Route C",
     ["06:45", "09:45", "12:45", "15:45", "18:45"]),
    ("Riverside Colony", "Bus Depot", "Feeder Bus", "Feeder Route C Return",
     ["07:30", "10:30", "13:30", "16:30", "19:30"]),
]

# ---------------------------------------------------------------------
# A few sample crowdsourced observations, referencing routes by their
# position (index) in SAMPLE_ROUTES above (0 = first route, etc.)
# Each entry: (route_index, observed_time, delay_minutes)
# ---------------------------------------------------------------------
SAMPLE_OBSERVATIONS = [
    (0, "06:05", 5),
    (0, "06:32", 2),
    (2, "07:10", 10),
    (4, "07:00", 0),
    (6, "06:20", 20),
]


def seed_database():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    # Start clean so re-running this script never creates duplicates.
    cursor.execute("DELETE FROM observations")
    cursor.execute("DELETE FROM timetable")
    cursor.execute("DELETE FROM routes")
    # Reset SQLite's internal auto-increment counters too, so IDs
    # start from 1 again each time you reseed.
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN "
                    "('routes', 'timetable', 'observations')")
    print("Cleared old data from routes, timetable, observations.")

    route_ids = []  # will store the route_id SQLite assigns to each route

    timetable_count = 0
    for source, destination, vehicle_type, route_name, times in SAMPLE_ROUTES:
        cursor.execute("""
            INSERT INTO routes (source, destination, vehicle_type, route_name)
            VALUES (?, ?, ?, ?)
        """, (source, destination, vehicle_type, route_name))

        route_id = cursor.lastrowid
        route_ids.append(route_id)

        for departure_time in times:
            cursor.execute("""
                INSERT INTO timetable (route_id, departure_time)
                VALUES (?, ?)
            """, (route_id, departure_time))
            timetable_count += 1

    print(f"Inserted {len(SAMPLE_ROUTES)} routes.")
    print(f"Inserted {timetable_count} timetable entries.")

    for route_index, observed_time, delay_minutes in SAMPLE_OBSERVATIONS:
        route_id = route_ids[route_index]
        cursor.execute("""
            INSERT INTO observations (route_id, observed_time, delay_minutes, submitted_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (route_id, observed_time, delay_minutes))

    print(f"Inserted {len(SAMPLE_OBSERVATIONS)} sample observations.")

    connection.commit()
    connection.close()

    print("Seeding complete.")


if __name__ == "__main__":
    seed_database()
