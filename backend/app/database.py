import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'barberflow.db')

def get_db_connection():
    """
    Returns a connection to the SQLite database.
    Enforces foreign keys and returns rows as dictionaries.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def execute_query(query: str, params: tuple = (), fetch_all: bool = True):
    """
    Executes a raw SQL query and returns results.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if fetch_all:
            result = [dict(row) for row in cursor.fetchall()]
        else:
            row = cursor.fetchone()
            result = dict(row) if row else None
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def execute_write(query: str, params: tuple = ()):
    """
    Executes an INSERT, UPDATE, or DELETE query and returns the last row ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        lastrowid = cursor.lastrowid
        conn.commit()
        return lastrowid
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
