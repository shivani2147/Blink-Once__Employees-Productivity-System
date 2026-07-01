"""
Migration: Add user_id column to notifications table for employee-targeted notifications.
Run once: python migrate_notifications_user_id.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "eps.db")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Check if column already exists
cur.execute("PRAGMA table_info(notifications)")
cols = [row[1] for row in cur.fetchall()]

if "user_id" not in cols:
    cur.execute("ALTER TABLE notifications ADD COLUMN user_id INTEGER REFERENCES users(id)")
    conn.commit()
    print("Added user_id column to notifications table.")
else:
    print("user_id column already exists -- no changes made.")

conn.close()
