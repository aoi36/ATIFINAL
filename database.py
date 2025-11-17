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
    print("   [DB] Defining new multi-user schema...")
    
    # --- [MODIFIED] SQL Schema is now multi-user ---
    schema_script = """
    PRAGMA foreign_keys = ON; /* Enforce foreign key constraints */

    /* 1. New User table (stores login) */
    CREATE TABLE IF NOT EXISTS user (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      lms_username TEXT UNIQUE NOT NULL,
      hashed_password TEXT NOT NULL,  /* <--- MODIFIED */
      google_calendar_id TEXT DEFAULT 'primary'
    );

    /* 2. Courses table (now linked to a user) */
    CREATE TABLE IF NOT EXISTS courses (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      lms_course_id INTEGER NOT NULL,
      user_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      url TEXT,
      FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
    );

    /* 3. Deadlines table (now linked to a user and the new course ID) */
    CREATE TABLE IF NOT EXISTS deadlines (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      course_db_id INTEGER NOT NULL,      /* Links to 'courses.id' (our local PK) */
      status TEXT,
      time_string TEXT,
      parsed_iso_date TEXT,
      url TEXT NOT NULL,
      is_completed INTEGER DEFAULT 0,
      FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
      FOREIGN KEY (course_db_id) REFERENCES courses (id) ON DELETE CASCADE
    );

    /* 4. User Content table (now linked to a user and the new course ID) */
    CREATE TABLE IF NOT EXISTS user_content (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      course_db_id INTEGER NOT NULL,
      source_file TEXT NOT NULL,
      type TEXT NOT NULL,
      user_question TEXT,
      content_json TEXT NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
      FOREIGN KEY (course_db_id) REFERENCES courses (id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS jwt_blocklist (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      jti TEXT NOT NULL UNIQUE,  /* 'jti' is the unique ID of a JWT */
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS assignments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      course_db_id INTEGER NOT NULL,      /* Links to 'courses.id' */
      title TEXT NOT NULL,
      url TEXT NOT NULL UNIQUE,         /* URL is the unique identifier */
      FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
      FOREIGN KEY (course_db_id) REFERENCES courses (id) ON DELETE CASCADE
    );

     CREATE TABLE IF NOT EXISTS chat_conversations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              title TEXT,
              ai_provider TEXT NOT NULL,
              course_db_id INTEGER,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
              FOREIGN KEY (course_db_id) REFERENCES courses (id) ON DELETE SET NULL
            );
        
      CREATE TABLE IF NOT EXISTS chat_messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              conversation_id INTEGER NOT NULL,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              attachments TEXT,
              token_count INTEGER,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (conversation_id) REFERENCES chat_conversations (id) ON DELETE CASCADE
            );
    """
    # --- End SQL Schema ---

    print("   [DB] Executing schema...")
    try:
        db_conn.executescript(schema_script) # Execute the schema script
        db_conn.commit()
        print("   [DB] Database tables created successfully.")
    except Exception as e:
        print(f"   [DB] ❌ Failed to create database tables: {e}")
        db_conn.rollback()
        raise

def setup_database():
    """
    Ensures the DB file AND tables exist before starting.
    This runs once at app startup, outside a request context.
    """
    print("[DB] Checking database integrity...")
    db = None # Initialize
    try:
        # Connect directly, not using Flask's 'g' object
        db = sqlite3.connect(DATABASE_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = db.cursor()
        
        # Check if the 'user' table exists (our new base table)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("[DB] Database tables already exist.")
        else:
            # If the file exists but tables are missing
            print("[DB] Tables not found. Initializing database...")
            # Pass the connection to init_db
            init_db(db) # This function will create tables and commit
            
    except Exception as e:
        print(f"[DB] ❌ Error during database setup: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if db:
            db.close()
            print("[DB] Database check complete.")
# --- END NEW DB HELPERS ---