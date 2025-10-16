"""
Migration: Remove price_per_kwh column from readings table

This migration removes the price_per_kwh column from the readings table.
The price should be fetched from settings at query time, not stored with each reading.
"""

import sqlite3
import os

def run_migration():
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'wattbox.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # SQLite doesn't support DROP COLUMN directly, so we need to:
        # 1. Create a new table without the price_per_kwh column
        # 2. Copy data from old table to new table
        # 3. Drop old table
        # 4. Rename new table to old name

        cursor.execute("""
            CREATE TABLE readings_new (
                id INTEGER PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                reading_kwh REAL NOT NULL,
                photo_path VARCHAR NOT NULL,
                processed_photo_path VARCHAR,
                source VARCHAR NOT NULL,
                device_id VARCHAR,
                battery_percent REAL,
                ocr_confidence REAL,
                manual_override BOOLEAN DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Copy data from old table to new table
        cursor.execute("""
            INSERT INTO readings_new (
                id, timestamp, reading_kwh, photo_path, processed_photo_path,
                source, device_id, battery_percent, ocr_confidence,
                manual_override, notes, created_at
            )
            SELECT
                id, timestamp, reading_kwh, photo_path, processed_photo_path,
                source, device_id, battery_percent, ocr_confidence,
                manual_override, notes, created_at
            FROM readings
        """)

        # Drop old table
        cursor.execute("DROP TABLE readings")

        # Rename new table
        cursor.execute("ALTER TABLE readings_new RENAME TO readings")

        conn.commit()
        print("✓ Successfully removed price_per_kwh column from readings table")

    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
