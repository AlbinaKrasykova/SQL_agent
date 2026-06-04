import sqlite3

DB_NAME = "health.db"

def get_connection():
    return sqlite3.connect(DB_NAME)