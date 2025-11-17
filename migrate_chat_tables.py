# migrate_chat_tables.py
# Run this script ONCE to add chat tables to your existing database

import sqlite3
import os

DATABASE_FILE = 'lms_data.db'

def migrate_database():
    """Adds chat tables to the existing database."""
    
    if not os.path.exists(DATABASE_FILE):
        print(f"❌ Database file '{DATABASE_FILE}' not found!")
        print("   Please run your main app first to create the database.")
        return False
    
    print(f"🔧 Migrating database: {DATABASE_FILE}")
    
    try:
        db = sqlite3.connect(DATABASE_FILE)
        cursor = db.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        print("   Creating chat_conversations table...")
        cursor.execute("""
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
            )
        """)
        
        print("   Creating chat_messages table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              conversation_id INTEGER NOT NULL,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              attachments TEXT,
              token_count INTEGER,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (conversation_id) REFERENCES chat_conversations (id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for better performance
        print("   Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user 
            ON chat_conversations(user_id, updated_at DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation 
            ON chat_messages(conversation_id, created_at ASC)
        """)
        
        db.commit()
        db.close()
        
        print("✅ Migration completed successfully!")
        print("   - chat_conversations table created")
        print("   - chat_messages table created")
        print("   - Indexes created for performance")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  LMS ASSISTANT - CHAT FEATURE DATABASE MIGRATION")
    print("="*60 + "\n")
    
    success = migrate_database()
    
    if success:
        print("\n🎉 You can now use the chat feature!")
        print("   Don't forget to add API keys to your .env file:")
        print("   - ANTHROPIC_API_KEY=sk-ant-...")
        print("   - OPENAI_API_KEY=sk-...")
        print("   - GOOGLE_API_KEY=AIza... (already configured)")
    else:
        print("\n❌ Migration failed. Please fix errors and try again.")
    
    print("\n" + "="*60 + "\n")