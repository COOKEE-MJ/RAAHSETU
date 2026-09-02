"""Create and safely upgrade the RaahSetu SQLite database.

Run from the project root with: python create_database.py
"""

import os
import sqlite3
from datetime import datetime, timedelta


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FOLDER = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_FOLDER, "routes.db")


def _create_tables(connection):
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS routes (
            route_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            destination TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            route_name TEXT
        );

        CREATE TABLE IF NOT EXISTS timetable (
            timetable_id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id INTEGER NOT NULL,
            departure_time TEXT NOT NULL,
            FOREIGN KEY (route_id) REFERENCES routes (route_id)
        );

        CREATE TABLE IF NOT EXISTS observations (
            observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_id INTEGER NOT NULL,
            observed_time TEXT NOT NULL,
            delay_minutes INTEGER NOT NULL DEFAULT 0,
            note TEXT,
            submitted_at TEXT NOT NULL,
            FOREIGN KEY (route_id) REFERENCES routes (route_id)
        );
        """
    )


def _migrate_legacy_schema(connection):
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if "routes" not in tables:
        return

    columns = {
        row[1] for row in connection.execute("PRAGMA table_info(routes)")
    }
    if "route_id" in columns:
        if "observations_legacy" in tables:
            legacy_count = connection.execute(
                "SELECT COUNT(*) FROM observations_legacy"
            ).fetchone()[0]
            if legacy_count == 0:
                connection.execute("DROP TABLE observations_legacy")
        return

    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("ALTER TABLE routes RENAME TO routes_legacy")
    if "observations" in tables:
        connection.execute(
            "ALTER TABLE observations RENAME TO observations_legacy"
        )
    _create_tables(connection)

    legacy_routes = connection.execute(
        """
        SELECT id, route_name, source, destination, mode,
               first_departure, last_departure, frequency_minutes
        FROM routes_legacy
        """
    ).fetchall()
    for route in legacy_routes:
        connection.execute(
            """
            INSERT INTO routes (route_id, source, destination, vehicle_type, route_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (route[0], route[2], route[3], route[4], route[1]),
        )
        first = datetime.strptime(route[5], "%H:%M")
        last = datetime.strptime(route[6], "%H:%M")
        current = first
        while current <= last:
            connection.execute(
                "INSERT INTO timetable (route_id, departure_time) VALUES (?, ?)",
                (route[0], current.strftime("%H:%M")),
            )
            current += timedelta(minutes=route[7])

    if "observations_legacy" in tables:
        connection.execute(
            """
            INSERT INTO observations
                (observation_id, route_id, observed_time, delay_minutes,
                 note, submitted_at)
            SELECT id, route_id, substr(submitted_at, 12, 5), delay_minutes,
                   note, submitted_at
            FROM observations_legacy
            """
        )
        connection.execute("DROP TABLE observations_legacy")
    connection.execute("DROP TABLE routes_legacy")
    connection.execute("PRAGMA foreign_keys = ON")


def create_database():
    os.makedirs(DATABASE_FOLDER, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        _migrate_legacy_schema(connection)
        _create_tables(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    print(f"Database ready at: {DATABASE_PATH}")
    print("Tables ready: routes, timetable, observations")


if __name__ == "__main__":
    create_database()
