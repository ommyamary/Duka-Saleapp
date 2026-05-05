import sqlite3
import os

db_path = 'saapos.db'
if not os.path.exists(db_path):
    print(f"Database {db_path} not found in {os.getcwd()}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if columns already exist
    cursor.execute("PRAGMA table_info(products)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'sku' not in columns:
        print("Adding 'sku' column to 'products' table...")
        cursor.execute("ALTER TABLE products ADD COLUMN sku TEXT")
    
    if 'qr_code' not in columns:
        print("Adding 'qr_code' column to 'products' table...")
        cursor.execute("ALTER TABLE products ADD COLUMN qr_code TEXT")
        
    if 'barcode' not in columns:
        print("Adding 'barcode' column to 'products' table...")
        cursor.execute("ALTER TABLE products ADD COLUMN barcode TEXT")
        
    conn.commit()
    print("Database schema updated successfully.")
except Exception as e:
    print(f"Error updating database: {e}")
finally:
    conn.close()
