import sys
import os

# Add current directory to path so we can import database
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

def run_migration():
    """
    Update User table to make username and password_hash nullable.
    This allows admin to pre-register employees without setting initial credentials.
    Employees will set their own password during self-registration.
    """
    with engine.connect() as conn:
        try:
            # Make username nullable (can be null until employee registers)
            conn.execute(text("ALTER TABLE users ALTER COLUMN username VARCHAR(150) NULL;"))
            print("✓ Updated username column to nullable")
            
            # Make password_hash nullable (will be set during employee self-registration)
            conn.execute(text("ALTER TABLE users ALTER COLUMN password_hash VARCHAR(255) NULL;"))
            print("✓ Updated password_hash column to nullable")
            
            conn.commit()
            print("\n✓ Migration completed successfully!")
            print("Employees can now be pre-registered without passwords.")
            print("They will set their password when they self-register using their email.")
            
        except Exception as e:
            print(f"Error during migration: {e}")
            conn.rollback()

if __name__ == "__main__":
    run_migration()
