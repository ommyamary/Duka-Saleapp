
import sqlite3
import os

db_path = "saapos.db"
if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if media_type column exists
    cursor.execute("PRAGMA table_info(advertisements)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "media_type" not in columns:
        print("Adding 'media_type' column to 'advertisements' table...")
        cursor.execute("ALTER TABLE advertisements ADD COLUMN media_type TEXT DEFAULT 'image'")
        conn.commit()
        print("Column 'media_type' added successfully.")
    else:
        print("Column 'media_type' already exists.")
        
except sqlite3.OperationalError as e:
    print(f"Error: {e}")
finally:
    conn.close()
