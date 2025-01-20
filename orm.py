import sqlite3
import os
import platform

class MiniORM:
    def __init__(self, db_name="settings.db"):
        system = platform.system()
        if system == "Linux":
            data_dir = os.path.expanduser("~/.local/share/LibreTranslateGUI/")
        elif system == "Windows":
            data_dir = os.path.join(os.getenv("APPDATA"), "LibreTranslateGUI")
        else:
            data_dir = os.path.expanduser("~/.local/share/LibreTranslateGUI/")

        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
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
        if row:
            return {"api_url": row[0], "api_key": row[1]}
        return None

    def get_language_settings(self):
        self.cursor.execute("""
        SELECT left_language, right_language FROM language_settings
        ORDER BY id DESC LIMIT 1
        """)
        row = self.cursor.fetchone()
        if row:
            return {"left_language": row[0], "right_language": row[1]}
        return None

    def close(self):
        self.connection.close()


