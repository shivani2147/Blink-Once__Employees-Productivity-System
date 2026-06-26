import sqlalchemy
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='productivity_edit_history'"))
    existing = {row[0] for row in result}
    missing_defs = []
    if 'old_values' not in existing:
        missing_defs.append('old_values NVARCHAR(MAX) NULL')
    if 'new_values' not in existing:
        missing_defs.append('new_values NVARCHAR(MAX) NULL')
    
    if missing_defs:
        alter_stmt = "ALTER TABLE productivity_edit_history ADD " + ", ".join(missing_defs)
        conn.execute(text(alter_stmt))
        print('Added missing columns:', missing_defs)
    else:
        print('All required columns already exist.')
