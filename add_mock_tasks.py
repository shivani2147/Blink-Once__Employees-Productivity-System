import datetime
import random
from database import SessionLocal
from models import User, ProductivityRecord, Attendance
from auth import get_password_hash

db = SessionLocal()

employees_data = [
    {"username": "manthan", "password": "6054", "name": "Manthan", "email": "manthan@blinkonce.com", "code": "EMP010", "num_records": 3},
    {"username": "shivani_2147", "password": "6054", "name": "Shivani", "email": "shivani@blinkonce.com", "code": "EMP011", "num_records": 4},
    {"username": "asdf_214", "password": "asdf", "name": "ASDF User", "email": "asdf@blinkonce.com", "code": "EMP012", "num_records": 2}
]

clients = ["Wedding Client A", "Corporate Client B", "Pre-wedding C", "Event D"]
projects = ["Highlight Video", "Teaser", "Full Event", "Reels"]
statuses = ["Done", "Ongoing", "Pending", "Hold"]

for data in employees_data:
    user = db.query(User).filter(User.username == data["username"]).first()
    
    if not user:
        # Check if email or code exists
        user = db.query(User).filter(User.email == data["email"]).first()
        if not user:
            print(f"Creating user {data['username']}...")
            user = User(
                username=data["username"],
                password_hash=get_password_hash(data["password"]),
                employee_name=data["name"],
                email=data["email"],
                employee_code=data["code"],
                role="Employee",
                department="Editing",
                designation="Video Editor",
                date_of_joining=datetime.date(2023, 1, 15)
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            print(f"User with email {data['email']} exists, updating username and password.")
            user.username = data["username"]
            user.password_hash = get_password_hash(data["password"])
            db.commit()
    else:
        print(f"User {data['username']} already exists. Updating password.")
        user.password_hash = get_password_hash(data["password"])
        db.commit()

    # First, delete existing records for this user to start fresh
    print(f"Deleting old records for {user.username}...")
    db.query(ProductivityRecord).filter(ProductivityRecord.user_id == user.id).delete()
    db.commit()

    # Generate random Productivity Records
    print(f"Adding {data['num_records']} Productivity Records for {user.username}...")
    for i in range(data['num_records']):
        # Create dates
        end_date = datetime.date.today() - datetime.timedelta(days=random.randint(0, 5))
        start_date = end_date - datetime.timedelta(days=random.randint(1, 3))
        deadline_date = end_date + datetime.timedelta(days=random.randint(-1, 2))
        
        record = ProductivityRecord(
            user_id=user.id,
            employee_name=user.employee_name,
            designation=user.designation,
            client_name=random.choice(clients),
            date=end_date,
            project_name=random.choice(projects),
            start_date=start_date,
            end_date=end_date,
            deadline_date=deadline_date,
            editing_type="Video Editing",
            video_duration=random.uniform(1.0, 5.0),
            status=random.choice(statuses),
            expected_workload_hours=random.uniform(5.0, 15.0)
        )
        db.add(record)
    
    db.commit()

print("Mock data successfully generated!")
