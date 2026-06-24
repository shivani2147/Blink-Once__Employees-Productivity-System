import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

cols = [
    ("employee_code", "VARCHAR(50)"),
    ("mobile_number", "VARCHAR(50)"),
    ("dob", "DATE"),
    ("gender", "VARCHAR(20)"),
    ("address", "VARCHAR(500)"),
    ("emergency_contact", "VARCHAR(50)"),
    ("photo_path", "VARCHAR(500)"),
    ("aadhaar_number", "VARCHAR(50)"),
    ("highest_qualification", "VARCHAR(200)"),
    ("institution_name", "VARCHAR(200)"),
    ("marksheet_path", "VARCHAR(500)"),
    ("date_of_joining", "DATE"),
    ("department", "VARCHAR(200)"),
    ("salary_type", "VARCHAR(50)"),
    ("salary_value", "VARCHAR(100)"),
    ("experience", "VARCHAR(50)"),
    ("skills", "TEXT"),
    ("software_knowledge", "TEXT"),
    ("camera_skill_level", "VARCHAR(100)"),
    ("resume_path", "VARCHAR(500)"),
    ("aadhaar_front_path", "VARCHAR(500)"),
    ("aadhaar_back_path", "VARCHAR(500)"),
    ("certificates_path", "VARCHAR(500)")
]


def run_migration():
    with engine.connect() as conn:
        for col, coltype in cols:
            try:
                conn.execute(text(
                    f"IF COL_LENGTH('users', '{col}') IS NULL BEGIN ALTER TABLE users ADD {col} {coltype}; END"
                ))
            except Exception as e:
                print(f"Error adding column {col}: {e}")
        conn.commit()
        print("Migration finished: employee-related columns ensured on users table")


if __name__ == '__main__':
    run_migration()
