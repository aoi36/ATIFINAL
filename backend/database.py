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

    /* ===== AI Learning Insights Tables ===== */

    /* Tracks learning progress per course */
    CREATE TABLE IF NOT EXISTS learning_progress (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      course_db_id INTEGER NOT NULL,
      completed_topics INTEGER DEFAULT 0,
      total_topics INTEGER DEFAULT 0,
      progress_percentage REAL DEFAULT 0.0,
      planned_completion_date TEXT,
      actual_completion_date TEXT,
      is_behind_schedule INTEGER DEFAULT 0,
      last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(user_id, course_db_id),
      FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
      FOREIGN KEY (course_db_id) REFERENCES courses (id) ON DELETE CASCADE
    );

    /* Records individual study sessions */
    CREATE TABLE IF NOT EXISTS study_sessions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      course_db_id INTEGER NOT NULL,
      session_date DATE NOT NULL,
      start_time TIME NOT NULL,
      end_time TIME NOT NULL,
      duration_minutes INTEGER NOT NULL,
      topics_studied TEXT,
      content_type TEXT,
      difficulty_level TEXT,
      focus_score REAL DEFAULT 0.0,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
      FOREIGN KEY (course_db_id) REFERENCES courses (id) ON DELETE CASCADE
    );

    /* Weekly statistics for trend analysis */
    CREATE TABLE IF NOT EXISTS weekly_stats (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      course_db_id INTEGER NOT NULL,
      week_start_date DATE NOT NULL,
      week_end_date DATE NOT NULL,
      total_study_hours REAL DEFAULT 0.0,
      sessions_count INTEGER DEFAULT 0,
      topics_completed INTEGER DEFAULT 0,
      average_focus_score REAL DEFAULT 0.0,
      quiz_average_score REAL DEFAULT 0.0,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
      FOREIGN KEY (course_db_id) REFERENCES courses (id) ON DELETE CASCADE
    );

    /* Learning patterns analysis */
    CREATE TABLE IF NOT EXISTS learning_patterns (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      preferred_study_time TEXT,
      optimal_session_duration INTEGER,
      most_productive_day TEXT,
      preferred_content_type TEXT,
      average_daily_study_hours REAL DEFAULT 0.0,
      learning_style TEXT,
      peak_focus_hours TEXT,
      last_analyzed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
    );

    /* AI-generated recommendations */
    CREATE TABLE IF NOT EXISTS ai_recommendations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      course_db_id INTEGER,
      recommendation_type TEXT NOT NULL,
      title TEXT NOT NULL,
      description TEXT NOT NULL,
      priority TEXT DEFAULT 'medium',
      is_addressed INTEGER DEFAULT 0,
      addressed_date TIMESTAMP,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      expires_at TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
      FOREIGN KEY (course_db_id) REFERENCES courses (id) ON DELETE SET NULL
    );

    /* Topics requiring improvement */
    CREATE TABLE IF NOT EXISTS weak_topics (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      course_db_id INTEGER NOT NULL,
      topic_name TEXT NOT NULL,
      last_quiz_score REAL DEFAULT 0.0,
      attempts_count INTEGER DEFAULT 0,
      last_attempted TIMESTAMP,
      recommendation_given INTEGER DEFAULT 0,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
      FOREIGN KEY (course_db_id) REFERENCES courses (id) ON DELETE CASCADE
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