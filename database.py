import json
import os
import sqlite3
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path="fruits.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    filename TEXT,
                    total_fruits INTEGER,
                    fruit_counts TEXT,
                    result_image TEXT,
                    processing_time REAL
                )
                """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE,
                    total_requests INTEGER,
                    total_fruits_detected INTEGER,
                    most_common_fruit TEXT
                )
                """
            )
            conn.commit()

    def save_request(self, filename, statistics, processing_time):
        fruit_counts_json = json.dumps(statistics["fruit_counts"])

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO requests (
                    filename, total_fruits, fruit_counts,
                    result_image, processing_time
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    filename,
                    statistics["total_fruits"],
                    fruit_counts_json,
                    statistics["result_image"],
                    processing_time,
                ),
            )
            conn.commit()

    def get_all_requests(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM requests ORDER BY timestamp DESC")
            rows = cursor.fetchall()

            requests = []
            for row in rows:
                request = dict(row)
                request["fruit_counts"] = json.loads(request["fruit_counts"])
                requests.append(request)

            return requests

    def get_daily_statistics(self):
        query = """
            SELECT
                DATE(timestamp) as date,
                COUNT(*) as total_requests,
                SUM(total_fruits) as total_fruits_detected,
                (
                    SELECT json_extract(fruit_counts, '$[0]')
                    FROM requests r2
                    WHERE DATE(r2.timestamp) = DATE(r1.timestamp)
                    GROUP BY json_extract(fruit_counts, '$[0]')
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                ) as most_common_fruit
            FROM requests r1
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()
