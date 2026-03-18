import sqlite3
import os

def apply_migration():
    db_path = os.path.join('instance', 'pos.db')
    if not os.path.exists(db_path):
        print("Database not found!")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("Adding stock_snapshot to stock_adjustments...")
        cursor.execute("ALTER TABLE stock_adjustments ADD COLUMN stock_snapshot INTEGER")
    except Exception as e:
        print(f"Migration skipped or failed: {e}")
        
    conn.commit()
    conn.close()
    print("Database migration complete.")

if __name__ == '__main__':
    apply_migration()
