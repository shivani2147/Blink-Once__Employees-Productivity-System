import sys
import os

# Add current directory to path so we can import database
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

def run_migration():
    with engine.connect() as conn:
        try:
            # For SQL Server
            conn.execute(text("ALTER TABLE productivity_records ALTER COLUMN estimated_completion_time VARCHAR(100);"))
            conn.commit()
            print("Successfully altered column estimated_completion_time to VARCHAR(100)")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_migration()
