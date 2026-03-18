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
        print("Adding user_id to customers...")
        cursor.execute("ALTER TABLE customers ADD COLUMN user_id INTEGER REFERENCES users(id)")
    except Exception as e:
        print(f"Customers update skipped or failed: {e}")
        
    try:
        print("Adding user_id to business_settings...")
        cursor.execute("ALTER TABLE business_settings ADD COLUMN user_id INTEGER REFERENCES users(id)")
    except Exception as e:
        print(f"Business settings update skipped or failed: {e}")
        
    conn.commit()
    conn.close()
    print("Database migration v2 complete.")

if __name__ == '__main__':
    apply_migration()
