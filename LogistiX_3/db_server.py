import sqlite3
import hashlib

class DataBase:
    def __init__(self):
        self.conn = sqlite3.connect('DataBase.db', check_same_thread=False)
        self.cur = self.conn.cursor()

        self.cur.execute("""CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE NOT NULL,
                            password TEXT NOT NULL
                        );""")
        self.conn.commit()

    def add_user(self, name, password):
        hash_password = hashlib.sha512(password.encode()).hexdigest()
        self.cur.execute('INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)', (name, hash_password))
        self.conn.commit()

    def get_user_password(self, username):
        self.cur.execute('SELECT password FROM users WHERE username = ?', (username,))
        result = self.cur.fetchone()
        if result:
            return result[0]
        return None