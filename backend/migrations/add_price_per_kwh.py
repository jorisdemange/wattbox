"""
Migration: Add price_per_kwh column to readings table

This migration adds the price_per_kwh column back to the readings table.
"""

import sqlite3
import os

def run_migration():
    # Get the database path - check multiple locations
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'wattbox.db'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'wattbox.db'),
        '/Users/joris/dev/wattbox/backend/wattbox.db'
    ]

    db_path = None
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break

    if not db_path:
        print(f"✗ Database not found. Tried: {possible_paths}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(readings)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'price_per_kwh' in columns:
            print("✓ price_per_kwh column already exists")
            return

        # Add price_per_kwh column with default value
        cursor.execute("""
            ALTER TABLE readings
            ADD COLUMN price_per_kwh REAL NOT NULL DEFAULT 0.42
        """)

        conn.commit()
        print("✓ Successfully added price_per_kwh column to readings table")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
