"""
Ensure Employee Details table structure exists and all required columns are present in users table.
This migration script ensures the users table has all columns needed for employee details.
"""

import pyodbc
from sqlalchemy import create_engine
from config import DATABASE_URL

try:
    engine = create_engine(DATABASE_URL)
    conn = engine.raw_connection()
    cursor = conn.cursor()
    
    print("✓ Connected to database")
    
    # Check if users table exists
    cursor.execute("""
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'users'
    """)
    
    if not cursor.fetchone():
        print("✗ Users table does not exist. Creating...")
        cursor.execute("""
            CREATE TABLE [dbo].[users] (
                [id] INT PRIMARY KEY IDENTITY(1,1),
                [employee_name] VARCHAR(150) NOT NULL,
                [employee_code] VARCHAR(50) UNIQUE,
                [email] VARCHAR(150) UNIQUE NOT NULL,
                [username] VARCHAR(150) UNIQUE NOT NULL,
                [password_hash] VARCHAR(255) NOT NULL,
                [designation] VARCHAR(150),
                [role] VARCHAR(50) DEFAULT 'Employee',
                [mobile_number] VARCHAR(50),
                [dob] DATE,
                [gender] VARCHAR(20),
                [address] VARCHAR(500),
                [emergency_contact] VARCHAR(50),
                [photo_path] VARCHAR(500),
                [aadhaar_number] VARCHAR(50),
                [highest_qualification] VARCHAR(200),
                [institution_name] VARCHAR(200),
                [marksheet_path] VARCHAR(500),
                [date_of_joining] DATE,
                [department] VARCHAR(200),
                [salary_type] VARCHAR(50),
                [salary_value] VARCHAR(100),
                [experience] VARCHAR(50),
                [skills] TEXT,
                [software_knowledge] TEXT,
                [camera_skill_level] VARCHAR(100),
                [resume_path] VARCHAR(500),
                [aadhaar_front_path] VARCHAR(500),
                [aadhaar_back_path] VARCHAR(500),
                [certificates_path] VARCHAR(500)
            )
        """)
        print("✓ Users table created")
    else:
        print("✓ Users table already exists")
    
    # List of required columns with their types
    required_columns = {
        'id': 'INT',
        'employee_name': 'VARCHAR(150)',
        'employee_code': 'VARCHAR(50)',
        'email': 'VARCHAR(150)',
        'username': 'VARCHAR(150)',
        'password_hash': 'VARCHAR(255)',
        'designation': 'VARCHAR(150)',
        'role': 'VARCHAR(50)',
        'mobile_number': 'VARCHAR(50)',
        'dob': 'DATE',
        'gender': 'VARCHAR(20)',
        'address': 'VARCHAR(500)',
        'emergency_contact': 'VARCHAR(50)',
        'photo_path': 'VARCHAR(500)',
        'aadhaar_number': 'VARCHAR(50)',
        'highest_qualification': 'VARCHAR(200)',
        'institution_name': 'VARCHAR(200)',
        'marksheet_path': 'VARCHAR(500)',
        'date_of_joining': 'DATE',
        'department': 'VARCHAR(200)',
        'salary_type': 'VARCHAR(50)',
        'salary_value': 'VARCHAR(100)',
        'experience': 'VARCHAR(50)',
        'skills': 'TEXT',
        'software_knowledge': 'TEXT',
        'camera_skill_level': 'VARCHAR(100)',
        'resume_path': 'VARCHAR(500)',
        'aadhaar_front_path': 'VARCHAR(500)',
        'aadhaar_back_path': 'VARCHAR(500)',
        'certificates_path': 'VARCHAR(500)'
    }
    
    # Get existing columns
    cursor.execute("""
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'users'
    """)
    
    existing_columns = {row[0].lower() for row in cursor.fetchall()}
    print(f"\n✓ Found {len(existing_columns)} existing columns in users table")
    
    # Add missing columns
    added_count = 0
    for col_name, col_type in required_columns.items():
        if col_name.lower() not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE [dbo].[users] ADD [{col_name}] {col_type}")
                print(f"  ✓ Added column: {col_name} ({col_type})")
                added_count += 1
            except Exception as e:
                print(f"  ✗ Failed to add column {col_name}: {e}")
        else:
            print(f"  ✓ Column exists: {col_name}")
    
    if added_count > 0:
        print(f"\n✓ Added {added_count} new columns to users table")
    else:
        print("\n✓ All required columns already exist")
    
    # Verify indexes
    cursor.execute("""
        SELECT INDEX_NAME FROM INFORMATION_SCHEMA.INDEXES 
        WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'email'
    """)
    
    if not cursor.fetchone():
        try:
            cursor.execute("CREATE UNIQUE INDEX idx_email ON [dbo].[users] ([email])")
            print("✓ Created unique index on email column")
        except:
            print("✓ Email index already exists or couldn't be created")
    
    cursor.execute("""
        SELECT INDEX_NAME FROM INFORMATION_SCHEMA.INDEXES 
        WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'employee_code'
    """)
    
    if not cursor.fetchone():
        try:
            cursor.execute("CREATE UNIQUE INDEX idx_employee_code ON [dbo].[users] ([employee_code])")
            print("✓ Created unique index on employee_code column")
        except:
            print("✓ Employee code index already exists or couldn't be created")
    
    conn.commit()
    print("\n✅ Database migration completed successfully!")
    
except Exception as e:
    print(f"❌ Error during migration: {e}")
    import traceback
    traceback.print_exc()

finally:
    try:
        cursor.close()
        conn.close()
    except:
        pass
