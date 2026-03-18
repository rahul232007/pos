from app import create_app
from extensions import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Migrating database - adding unit column to products table...")
    try:
        # Check if column exists
        with db.engine.connect() as conn:
            # SQLite specific pragmas or just try add
            try:
                conn.execute(text("ALTER TABLE products ADD COLUMN unit VARCHAR(20) DEFAULT 'pcs'"))
                print("Column 'unit' added successfully.")
            except Exception as e:
                print(f"Migration result (may already exist): {e}")
                
        print("Migration complete.")
    except Exception as e:
        print(f"Error during migration: {e}")
