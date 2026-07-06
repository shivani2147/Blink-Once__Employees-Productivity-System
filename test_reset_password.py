from database import SessionLocal
from models import User
from auth import get_password_hash

db = SessionLocal()
u = db.query(User).filter(User.employee_code == 'EMP022').first()

if u:
    new_password = "test123"
    u.password_hash = get_password_hash(new_password)
    db.commit()
    print(f"Password reset for {u.email} to: test123")
else:
    print("Employee not found")
