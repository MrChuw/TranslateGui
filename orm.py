import sqlite3
import os

class MiniORM:
    def __init__(self, data_dir, db_name="settings.db"):
        self.db_path = os.path.join(data_dir, db_name)
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_url TEXT NOT NULL,
            api_key TEXT NOT NULL
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS language_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            left_language TEXT NOT NULL,
            right_language TEXT NOT NULL
        )
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS translation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_language TEXT NOT NULL,
            target_language TEXT NOT NULL,
            input_text TEXT NOT NULL,
            output_text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.connection.commit()

    def save_api_settings(self, api_url, api_key):
        self.cursor.execute("""
        INSERT INTO api_settings (api_url, api_key)
        VALUES (?, ?)
        """, (api_url, api_key))
        self.connection.commit()

    def save_language_settings(self, left_language, right_language):
        self.cursor.execute("""
        INSERT INTO language_settings (left_language, right_language)
        VALUES (?, ?)
        """, (left_language, right_language))
        self.connection.commit()

    def get_api_settings(self):
        self.cursor.execute("""
        SELECT api_url, api_key FROM api_settings
        ORDER BY id DESC LIMIT 1
        """)
        row = self.cursor.fetchone()
        return {"api_url": row[0], "api_key": row[1]} if row else None

    def get_language_settings(self):
        self.cursor.execute("""
        SELECT left_language, right_language FROM language_settings
        ORDER BY id DESC LIMIT 1
        """)
        row = self.cursor.fetchone()
        return {"left_language": row[0], "right_language": row[1]} if row else None

    def add_translation_history(self, source_language, target_language, input_text, output_text):
        self.cursor.execute("""
        INSERT INTO translation_history (source_language, target_language, input_text, output_text)
        VALUES (?, ?, ?, ?)
        """, (source_language, target_language, input_text, output_text))
        self.connection.commit()

    def get_translation_history(self, limit=100):
        self.cursor.execute("""
        SELECT source_language, target_language, input_text, output_text, timestamp 
        FROM translation_history
        ORDER BY timestamp DESC
        LIMIT ?
        """, (limit,))
        rows = self.cursor.fetchall()
        return [
            {
                "source_language": row[0],
                "target_language": row[1],
                "input_text": row[2],
                "output_text": row[3],
                "timestamp": row[4]
            }
            for row in rows
        ]

    def clear_translation_history(self):
        # Execute the DELETE statement to remove all records from the translation_history table
        self.cursor.execute("DELETE FROM translation_history")
        self.connection.commit()


    def close(self):
        self.connection.close()


