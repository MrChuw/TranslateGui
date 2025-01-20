import sqlite3
import json

class MiniORM:
    def __init__(self, db_name="settings.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self._create_tables()

    def _create_tables(self):
        # Cria tabelas para armazenar os dados
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
        # Salva configurações da API
        self.cursor.execute("""
        INSERT INTO api_settings (api_url, api_key)
        VALUES (?, ?)
        """, (api_url, api_key))
        self.connection.commit()

    def save_language_settings(self, left_language, right_language):
        # Salva configurações de idiomas
        self.cursor.execute("""
        INSERT INTO language_settings (left_language, right_language)
        VALUES (?, ?)
        """, (left_language, right_language))
        self.connection.commit()

    def get_api_settings(self):
        # Recupera a última configuração de API salva
        self.cursor.execute("""
        SELECT api_url, api_key FROM api_settings
        ORDER BY id DESC LIMIT 1
        """)
        row = self.cursor.fetchone()
        if row:
            return {"api_url": row[0], "api_key": row[1]}
        return None

    def get_language_settings(self):
        # Recupera a última configuração de idiomas salva
        self.cursor.execute("""
        SELECT left_language, right_language FROM language_settings
        ORDER BY id DESC LIMIT 1
        """)
        row = self.cursor.fetchone()
        if row:
            return {"left_language": row[0], "right_language": row[1]}
        return None

    def close(self):
        # Fecha a conexão com o banco de dados
        self.connection.close()


