import sqlite3
import os

DB_PATH = "wardrobe.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found. Nothing to migrate.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Create users table if it doesn't exist (just in case)
        # We'll rely on SQLAlchemy to create it properly mostly, but for FK we need it.
        # Actually, let's just add the column. If users table doesn't exist, the FK constraint might be harmless until enforced?
        # SQLite enforces FKs only if PRAGMA foreign_keys=ON.
        
        # Check if user_id column exists
        cursor.execute("PRAGMA table_info(clothing_items)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "user_id" in columns:
            print("Column 'user_id' already exists in 'clothing_items'.")
        else:
            print("Adding 'user_id' column to 'clothing_items'...")
            # SQLite doesn't support ADD COLUMN with Constraints easily in older versions, 
            # but usually ADD COLUMN user_id INTEGER works.
            cursor.execute("ALTER TABLE clothing_items ADD COLUMN user_id INTEGER")
            print("Column added.")
            
            # Optional: Assign existing items to a default user ID if needed?
            # For now, we'll leave them as NULL (if nullable) or 0. 
            # The model definition probably enforces a relationship.
            
        conn.commit()
        print("Migration complete.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
