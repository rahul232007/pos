import sqlite3
import os

def apply_cleanup():
    db_path = os.path.join('instance', 'pos.db')
    if not os.path.exists(db_path):
        print("Database not found!")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Dropping categories table...")
        cursor.execute("DROP TABLE IF EXISTS categories")
    except Exception as e:
        print(f"Error dropping categories: {e}")
        
    # SQLite doesn't support dropping columns easily in older versions, 
    # but since this is local dev we might just leave the column or 
    # do a full table recreation. For now, just dropping the table is the main part.
    # The app won't use the column anyway.
        
    conn.commit()
    conn.close()
    print("Database cleanup complete.")

if __name__ == '__main__':
    apply_cleanup()
