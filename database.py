# database.py
import sqlite3
import os
from flask import g
from config import DATABASE_FILE # Import from your new config

def get_db():
    """Opens a new database connection for the current request context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_connection(exception):
    """Closes the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(db_conn):
    """Initializes the database by creating tables. schema.sql is no longer needed."""
    print("   [DB] Defining schema...")
    schema_script = """
    PRAGMA foreign_keys = ON;
    CREATE TABLE IF NOT EXISTS courses (
      course_id INTEGER PRIMARY KEY, name TEXT NOT NULL, url TEXT
    );
    CREATE TABLE IF NOT EXISTS deadlines (
      id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER NOT NULL, status TEXT,
      time_string TEXT, parsed_iso_date TEXT, url TEXT NOT NULL,
      FOREIGN KEY (course_id) REFERENCES courses (course_id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS user_content (
      id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER NOT NULL, source_file TEXT NOT NULL,
      type TEXT NOT NULL, user_question TEXT, content_json TEXT NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (course_id) REFERENCES courses (course_id) ON DELETE CASCADE
    );
    """
    print("   [DB] Executing schema...")
    try:
        db_conn.executescript(schema_script)
        db_conn.commit()
        print("   [DB] Database tables created successfully.")
    except Exception as e:
        print(f"   [DB] ❌ Failed to create database tables: {e}")
        db_conn.rollback()
        raise

def setup_database():
    """Ensures the DB file AND tables exist before starting."""
    print("[DB] Checking database integrity...")
    db = None
    try:
        db = sqlite3.connect(DATABASE_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='courses'")
        if cursor.fetchone():
            print("[DB] Database tables already exist.")
        else:
            print("[DB] Tables not found. Initializing database...")
            init_db(db)
    except Exception as e:
        print(f"[DB] ❌ Error during database setup: {e}")
    finally:
        if db:
            db.close()
            print("[DB] Database check complete.")