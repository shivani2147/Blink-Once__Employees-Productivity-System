from database import engine
from sqlalchemy import text

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE notifications ADD user_id INT NULL"))
        # we don't necessarily need the foreign key constraint immediately, but let's just add the column for now
    print("Added column user_id to notifications")
except Exception as e:
    print("Error:", e)
