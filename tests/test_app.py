import os
import sqlite3
import tempfile
import unittest

import app
import create_database


class RaahSetuAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_path = os.path.join(
            tempfile.gettempdir(), "raahsetu_test.db"
        )
        if os.path.exists(cls.database_path):
            os.remove(cls.database_path)
        app.DATABASE_PATH = cls.database_path
        create_database.DATABASE_PATH = cls.database_path
        app.init_db()
        connection = sqlite3.connect(cls.database_path)
        connection.execute(
            """
            INSERT INTO routes (source, destination, vehicle_type, route_name)
            VALUES (?, ?, ?, ?)
            """,
            ("Test Station", "Test College", "Local Bus", "Test Route"),
        )
        connection.executemany(
            "INSERT INTO timetable (route_id, departure_time) VALUES (1, ?)",
            [("08:00",), ("09:00",)],
        )
        connection.executemany(
            """
            INSERT INTO observations
                (route_id, observed_time, delay_minutes, note, submitted_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (1, "08:05", 5, "Minor delay", "2026-09-02T08:05:00"),
                (1, "09:20", 20, "Severe delay", "2026-09-02T09:20:00"),
            ],
        )
        connection.commit()
        connection.close()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.database_path):
            os.remove(cls.database_path)

    def setUp(self):
        self.client = app.app.test_client()

    def test_homepage_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Recent Reports", response.data)

    def test_search_returns_timetable_and_next_departure(self):
        response = self.client.get(
            "/search?source=test&destination=college"
        )
        route = response.get_json()["routes"][0]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(route["timetable"], ["08:00", "09:00"])
        self.assertIn(route["next_departure"], route["timetable"])

    def test_reports_page_groups_and_counts_route_reports(self):
        response = self.client.get("/reports")
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Most delayed route", html)
        self.assertIn("2 reports for this route", html)
        self.assertIn("Severe delay", html)

    def test_submit_report(self):
        response = self.client.post(
            "/submit-observation",
            json={"route_id": 1, "delay_minutes": 3, "note": "New report"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["message"], "Report submitted.")


if __name__ == "__main__":
    unittest.main()
