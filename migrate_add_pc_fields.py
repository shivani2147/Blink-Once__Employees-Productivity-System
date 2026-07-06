import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text


def run_migration():
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "IF COL_LENGTH('productivity_records', 'pc_number') IS NULL "
                "BEGIN ALTER TABLE productivity_records ADD pc_number VARCHAR(100); END"
            ))
            conn.commit()
            print("Ensured pc_number exists on productivity_records")
        except Exception as e:
            conn.rollback()
            print(f"Error ensuring pc_number: {e}")

        try:
            conn.execute(text(
                "IF COL_LENGTH('productivity_records', 'uploaded_to_drive') IS NULL "
                "BEGIN ALTER TABLE productivity_records ADD uploaded_to_drive BIT DEFAULT 0; END"
            ))
            conn.commit()
            print("Ensured uploaded_to_drive exists on productivity_records")
        except Exception as e:
            conn.rollback()
            print(f"Error ensuring uploaded_to_drive: {e}")

        try:
            conn.execute(text(
                "IF COL_LENGTH('productivity_records', 'drive_link') IS NULL "
                "BEGIN ALTER TABLE productivity_records ADD drive_link VARCHAR(500); END"
            ))
            conn.commit()
            print("Ensured drive_link exists on productivity_records")
        except Exception as e:
            conn.rollback()
            print(f"Error ensuring drive_link: {e}")


if __name__ == "__main__":
    run_migration()
