from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    employee_name = Column(String(150), nullable=False)
    employee_code = Column(String(50), unique=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    username = Column(String(150), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    designation = Column(String(150))
    role = Column(String(50), default="Employee") # Admin or Employee
    mobile_number = Column(String(50))
    dob = Column(Date)
    gender = Column(String(20))
    address = Column(String(500))
    emergency_contact = Column(String(50))
    photo_path = Column(String(500))
    aadhaar_number = Column(String(50))
    highest_qualification = Column(String(200))
    institution_name = Column(String(200))
    marksheet_path = Column(String(500))
    date_of_joining = Column(Date)
    department = Column(String(200))
    salary_type = Column(String(50))
    salary_value = Column(String(100))
    salary_amount = Column(Float)
    experience = Column(String(50))
    skills = Column(Text)
    software_knowledge = Column(Text)
    camera_skill_level = Column(String(100))
    resume_path = Column(String(500))
    aadhaar_front_path = Column(String(500))
    aadhaar_back_path = Column(String(500))
    certificates_path = Column(String(500))

    records = relationship("ProductivityRecord", back_populates="user")
    attendance_records = relationship("Attendance", back_populates="user")
    leave_requests = relationship("LeaveRequest", back_populates="user")

class ProductivityRecord(Base):
    __tablename__ = "productivity_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # Details copied for easy querying/reporting, though linked to user
    employee_name = Column(String(150))
    designation = Column(String(150))
    
    client_name = Column(String(200))
    date = Column(Date)
    project_name = Column(String(200))
    start_date = Column(Date)
    end_date = Column(Date)
    deadline_date = Column(Date)
    editing_type = Column(String(200))
    
    video_duration = Column(Float) # in hours or minutes
    status = Column(String(50), default="Pending") # Pending, In Progress, Completed
    priority = Column(String(50), default="Medium") # Low, Medium, High
    task_description = Column(Text)
    
    harddisk_number = Column(String(100))
    harddisk_directory = Column(String(255))
    
    uploaded_to_drive = Column(Boolean, default=False)
    drive_link = Column(String(500))
    
    shoot_type = Column(String(100)) # engagement, wedding, etc.
    cameras_used = Column(Integer, default=1)
    
    comments = Column(Text)
    
    expected_workload_hours = Column(Float)
    estimated_completion_time = Column(String(100)) # e.g. '1 day 2 hours'

    user = relationship("User", back_populates="records")

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, index=True)
    status = Column(String(50)) # Present, Absent, Late
    time_in = Column(String(50), nullable=True) # E.g., '09:00 AM'
    time_out = Column(String(50), nullable=True) # E.g., '06:00 PM'

    user = relationship("User", back_populates="attendance_records")

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    start_date = Column(Date)
    end_date = Column(Date)
    leave_type = Column(String(100)) # e.g. Sick Leave, Casual Leave
    reason = Column(Text)
    status = Column(String(50), default="Pending") # Pending, Approved, Rejected

    user = relationship("User", back_populates="leave_requests")
