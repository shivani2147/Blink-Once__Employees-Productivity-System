from database import engine
from sqlalchemy import text
with engine.connect() as conn:
    res = conn.execute(text("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='leave_balance'"))
    print([r[0] for r in res])
