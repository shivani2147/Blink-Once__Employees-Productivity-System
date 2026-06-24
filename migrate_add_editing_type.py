import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text


def run_migration():
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "IF COL_LENGTH('productivity_records', 'editing_type') IS NULL "
                "BEGIN ALTER TABLE productivity_records ADD editing_type VARCHAR(200); END"
            ))
            conn.commit()
            print("Successfully ensured editing_type column exists on productivity_records")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    run_migration()
