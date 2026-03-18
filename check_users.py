import sqlite3
import os

db_path = 'c:/Users/rahul/OneDrive/Desktop/Projects/pcos/instance/pos.db'
if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username, role, is_approved FROM users")
    users = cursor.fetchall()
    
    print(f"{'ID':<5} {'Username':<15} {'Role':<10} {'Approved':<10}")
    print("-" * 45)
    for u in users:
        print(f"{u[0]:<5} {u[1]:<15} {u[2]:<10} {u[3]:<10}")
    
    conn.close()
except Exception as e:
    print(f"Error: {e}")
