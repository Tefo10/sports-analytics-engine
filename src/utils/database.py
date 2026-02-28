import sqlite3
from datetime import datetime
import os

class DBManager:
    def __init__(self, db_path="data/soccer_bot.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, joined_at DATETIME)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, action TEXT, query TEXT, timestamp DATETIME)''')

    def register_user(self, u_id, nick, name):
        with self._get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO users VALUES (?,?,?,?)", (u_id, nick, name, datetime.now()))

    def log_event(self, u_id, action, query=""):
        with self._get_conn() as conn:
            conn.execute("INSERT INTO logs (user_id, action, query, timestamp) VALUES (?,?,?,?)", (u_id, action, query, datetime.now()))
            
    def get_all_users(self):
        with self._get_conn() as conn:
            return [row[0] for row in conn.execute("SELECT user_id FROM users").fetchall()]
