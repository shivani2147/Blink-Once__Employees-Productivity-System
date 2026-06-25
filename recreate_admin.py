"""
Run this script once to recreate the default admin account after truncating tables.
Usage: python recreate_admin.py
"""
from database import SessionLocal
from models import User
from auth import get_password_hash

db = SessionLocal()

try:
    existing = db.query(User).filter(User.role == "Admin").first()
    if existing:
        print(f"Admin already exists: username='{existing.username}'")
    else:
        admin = User(
            employee_name="System Admin",
            email="admin@blinkonce.local",
            username="admin",
            password_hash=get_password_hash("admin123"),
            designation="Administrator",
            role="Admin"
        )
        db.add(admin)
        db.commit()
        print("✅ Admin account recreated successfully!")
        print("   Username : admin")
        print("   Password : admin123")
finally:
    db.close()
