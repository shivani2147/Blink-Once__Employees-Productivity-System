import sys
import os
import datetime
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
from models import Base, User, Attendance, LeaveRequest

def run_migration():
    print("Creating new tables...")
    Base.metadata.create_all(bind=engine)
    print("Successfully created Attendance and LeaveRequest tables.")
    
    # Generate some mock data for existing employees
    db = SessionLocal()
    try:
        employees = db.query(User).filter(User.role == "Employee").all()
        if not employees:
            print("No employees found. Skipping mock data generation.")
            return

        today = datetime.date.today()
        # Create attendance for the last 30 days
        for i in range(30):
            current_date = today - datetime.timedelta(days=i)
            # Skip weekends just for realism, or not
            if current_date.weekday() >= 6: # Sunday
                continue
                
            for emp in employees:
                # 80% Present, 10% Absent, 10% Late
                status = random.choices(["Present", "Absent", "Late"], weights=[80, 10, 10])[0]
                
                # Check if record already exists
                existing = db.query(Attendance).filter(Attendance.user_id == emp.id, Attendance.date == current_date).first()
                if not existing:
                    att = Attendance(
                        user_id=emp.id,
                        date=current_date,
                        status=status,
                        time_in="09:00 AM" if status == "Present" else ("10:30 AM" if status == "Late" else None),
                        time_out="06:00 PM" if status in ["Present", "Late"] else None
                    )
                    db.add(att)
        
        # Add a couple of pending leave requests
        for emp in employees[:2]:
            existing_leave = db.query(LeaveRequest).filter(LeaveRequest.user_id == emp.id).first()
            if not existing_leave:
                lr = LeaveRequest(
                    user_id=emp.id,
                    start_date=today + datetime.timedelta(days=1),
                    end_date=today + datetime.timedelta(days=2),
                    reason="Personal work",
                    status="Pending"
                )
                db.add(lr)
        
        db.commit()
        print("Mock attendance data populated.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
