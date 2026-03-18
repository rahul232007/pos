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
        print("Adding company_name to users...")
        cursor.execute("ALTER TABLE users ADD COLUMN company_name TEXT")
    except Exception as e:
        print(f"Users update skipped or failed: {e}")
        
    # Populate existing users
    try:
        cursor.execute("UPDATE users SET company_name = 'Quantum POS' WHERE company_name IS NULL")
    except Exception as e:
        print(f"Population failed: {e}")
        
    conn.commit()
    conn.close()
    print("Database migration complete.")

if __name__ == '__main__':
    apply_migration()
