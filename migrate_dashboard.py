from database import engine
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, OperationalError

def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE productivity_records ADD priority VARCHAR(50) DEFAULT 'Medium'"))
            conn.commit()
            print("Added 'priority' to productivity_records")
        except Exception as e:
            conn.rollback()
            print(f"Column 'priority' might already exist: {e}")

        try:
            conn.execute(text("ALTER TABLE productivity_records ADD task_description TEXT"))
            conn.commit()
            print("Added 'task_description' to productivity_records")
        except Exception as e:
            conn.rollback()
            print(f"Column 'task_description' might already exist: {e}")

        try:
            conn.execute(text("ALTER TABLE leave_requests ADD leave_type VARCHAR(100)"))
            conn.commit()
            print("Added 'leave_type' to leave_requests")
        except Exception as e:
            conn.rollback()
            print(f"Column 'leave_type' might already exist: {e}")

        # Map existing statuses
        print("Mapping statuses to new format...")
        conn.execute(text("UPDATE productivity_records SET status = 'Completed' WHERE status IN ('Done')"))
        conn.execute(text("UPDATE productivity_records SET status = 'In Progress' WHERE status IN ('Ongoing')"))
        conn.execute(text("UPDATE productivity_records SET status = 'Pending' WHERE status IN ('Not Started', 'Hold')"))
        conn.commit()
        
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
