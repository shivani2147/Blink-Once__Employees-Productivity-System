"""
Migration: Add Employee Dashboard Features
==========================================
Adds new columns to existing tables and creates new tables for MS SQL Server.
Run once: python migrate_employee_features.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import engine
from sqlalchemy import text
import datetime

def col_exists(conn, table, column):
    result = conn.execute(text(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": table, "c": column})
    return result.scalar() > 0

def table_exists(conn, table):
    result = conn.execute(text(
        "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = :t"
    ), {"t": table})
    return result.scalar() > 0

def run_migration():
    with engine.begin() as conn:
        print("=" * 60)
        print("Employee Features Migration -- MS SQL Server")
        print("=" * 60)

        # 1. Extend attendance table
        print("\n[1] Extending attendance table...")
        att_cols = {
            "latitude":        "ALTER TABLE attendance ADD latitude FLOAT NULL",
            "longitude":       "ALTER TABLE attendance ADD longitude FLOAT NULL",
            "working_hours":   "ALTER TABLE attendance ADD working_hours FLOAT NULL",
            "day_type":        "ALTER TABLE attendance ADD day_type NVARCHAR(50) NULL",
            "half_day_reason": "ALTER TABLE attendance ADD half_day_reason NVARCHAR(MAX) NULL",
        }
        for col, sql in att_cols.items():
            if not col_exists(conn, "attendance", col):
                conn.execute(text(sql))
                print(f"   [OK] Added attendance.{col}")
            else:
                print(f"   [--] Skip attendance.{col} (already exists)")

        # 2. Extend leave_requests table
        print("\n[2] Extending leave_requests table...")
        lr_cols = {
            "days_count":  "ALTER TABLE leave_requests ADD days_count INT NULL",
            "approved_by": "ALTER TABLE leave_requests ADD approved_by INT NULL",
        }
        for col, sql in lr_cols.items():
            if not col_exists(conn, "leave_requests", col):
                conn.execute(text(sql))
                print(f"   [OK] Added leave_requests.{col}")
            else:
                print(f"   [--] Skip leave_requests.{col} (already exists)")

        # 3. Create leave_balance
        print("\n[3] Creating leave_balance table...")
        if not table_exists(conn, "leave_balance"):
            conn.execute(text("""
                CREATE TABLE leave_balance (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    user_id INT NOT NULL UNIQUE,
                    year INT NOT NULL,
                    total_leaves INT NOT NULL DEFAULT 12,
                    used_leaves INT NOT NULL DEFAULT 0,
                    remaining_leaves INT NOT NULL DEFAULT 12,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))
            print("   [OK] Created leave_balance")
        else:
            print("   [--] Skip leave_balance creation (already exists)")
            # Ensure required columns exist
            missing_cols = {
                "used_leaves": "ALTER TABLE leave_balance ADD used_leaves INT NOT NULL DEFAULT 0",
                "remaining_leaves": "ALTER TABLE leave_balance ADD remaining_leaves INT NOT NULL DEFAULT 12",
            }
            for col, sql in missing_cols.items():
                if not col_exists(conn, "leave_balance", col):
                    conn.execute(text(sql))
                    print(f"   [OK] Added leave_balance.{col}")
                else:
                    print(f"   [--] Skip leave_balance.{col} (already exists)")

        # 4. Create holidays
        print("\n[4] Creating holidays table...")
        if not table_exists(conn, "holidays"):
            conn.execute(text("""
                CREATE TABLE holidays (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    name NVARCHAR(200) NOT NULL,
                    date DATE NOT NULL,
                    day NVARCHAR(20) NULL,
                    description NVARCHAR(MAX) NULL,
                    holiday_type NVARCHAR(50) NOT NULL DEFAULT 'National',
                    is_active BIT NOT NULL DEFAULT 1
                )
            """))
            print("   [OK] Created holidays")
        else:
            print("   [--] Skip holidays (already exists)")

        # 5. Create productivity_edit_history
        print("\n[5] Creating productivity_edit_history table...")
        if not table_exists(conn, "productivity_edit_history"):
            conn.execute(text("""
                CREATE TABLE productivity_edit_history (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    record_id INT NOT NULL,
                    user_id INT NOT NULL,
                    edited_at DATETIME NOT NULL DEFAULT GETDATE(),
                    old_values NVARCHAR(MAX) NULL,
                    new_values NVARCHAR(MAX) NULL,
                    FOREIGN KEY (record_id) REFERENCES productivity_records(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """))
            print("   [OK] Created productivity_edit_history")
        else:
            print("   [--] Skip productivity_edit_history (already exists)")

        # 6. Create office_location
        print("\n[6] Creating office_location table...")
        if not table_exists(conn, "office_location"):
            conn.execute(text("""
                CREATE TABLE office_location (
                    id INT IDENTITY(1,1) PRIMARY KEY,
                    name NVARCHAR(200) NOT NULL DEFAULT 'Main Office',
                    latitude FLOAT NOT NULL,
                    longitude FLOAT NOT NULL,
                    radius_meters INT NOT NULL DEFAULT 100,
                    is_active BIT NOT NULL DEFAULT 1
                )
            """))
            print("   [OK] Created office_location")
            conn.execute(text("""
                INSERT INTO office_location (name, latitude, longitude, radius_meters, is_active)
                VALUES ('Main Office', 28.6139, 77.2090, 100, 1)
            """))
            print("   [OK] Inserted default office location (update via Admin > Settings)")
        else:
            print("   [--] Skip office_location (already exists)")

        # 7. Seed leave_balance for existing employees
        print("\n[7] Seeding leave_balance for existing employees...")
        year = datetime.datetime.now().year
        employees = conn.execute(text(
            "SELECT id FROM users WHERE role = 'Employee'"
        )).fetchall()
        seeded = 0
        for emp in employees:
            exists = conn.execute(text(
                "SELECT COUNT(*) FROM leave_balance WHERE user_id = :uid"
            ), {"uid": emp[0]}).scalar()
            if not exists:
                conn.execute(text(
                    "INSERT INTO leave_balance (user_id, year, total_leaves, used_leaves, remaining_leaves) "
                    "VALUES (:uid, :yr, 12, 0, 12)"
                ), {"uid": emp[0], "yr": year})
                seeded += 1
        print(f"   [OK] Seeded leave_balance for {seeded} employee(s)")

        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)

if __name__ == "__main__":
    run_migration()
