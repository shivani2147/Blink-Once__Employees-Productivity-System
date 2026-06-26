from sqlalchemy import Column, Integer, String, Float, Boolean, Date, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

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
    leave_requests = relationship("LeaveRequest", back_populates="user", foreign_keys="[LeaveRequest.user_id]")
    leave_balance = relationship("LeaveBalance", back_populates="user", uselist=False)

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
    harddisk_directory = Column(String(255))  # UI label: "Folder Name" (optional)
    
    uploaded_to_drive = Column(Boolean, default=False)
    drive_link = Column(String(500))
    
    shoot_type = Column(String(100)) # engagement, wedding, etc.
    cameras_used = Column(Integer, default=1)
    
    comments = Column(Text)
    
    expected_workload_hours = Column(Float)
    estimated_completion_time = Column(String(100)) # e.g. '1 day 2 hours'

    user = relationship("User", back_populates="records")
    edit_history = relationship("ProductivityEditHistory", back_populates="record")

class ProductivityEditHistory(Base):
    """Audit log for all edits made to productivity records by employees."""
    __tablename__ = "productivity_edit_history"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("productivity_records.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    edited_at = Column(DateTime, default=datetime.datetime.utcnow)
    old_values = Column(Text)   # JSON string of fields before edit
    new_values = Column(Text)   # JSON string of fields after edit

    record = relationship("ProductivityRecord", back_populates="edit_history")

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, index=True)
    status = Column(String(50))  # Present, Absent, Late, Half Day
    time_in = Column(String(50), nullable=True)   # e.g., '09:00 AM'
    time_out = Column(String(50), nullable=True)  # e.g., '06:00 PM'
    # New GPS & working hours fields
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    working_hours = Column(Float, nullable=True)          # computed on punch-out
    day_type = Column(String(50), nullable=True)          # Full Day, Half Day, Short Day
    half_day_reason = Column(Text, nullable=True)         # mandatory if half day

    user = relationship("User", back_populates="attendance_records")

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    start_date = Column(Date)
    end_date = Column(Date)
    leave_type = Column(String(100))  # Annual, Sick, Casual, etc.
    reason = Column(Text)
    status = Column(String(50), default="Pending")  # Pending, Approved, Rejected
    days_count = Column(Integer, nullable=True)       # number of leave days applied
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    user = relationship("User", back_populates="leave_requests", foreign_keys=[user_id])

class LeaveBalance(Base):
    """Tracks each employee's annual leave allocation and usage."""
    __tablename__ = "leave_balance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    year = Column(Integer, default=datetime.datetime.utcnow().year)
    total_leaves = Column(Integer, default=12)
    used_leaves = Column(Integer, default=0)
    remaining_leaves = Column(Integer, default=12)

    user = relationship("User", back_populates="leave_balance")

class Holiday(Base):
    """Holiday calendar managed by Admin."""
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    date = Column(Date, nullable=False)
    day = Column(String(20))                               # e.g., Monday
    description = Column(Text, nullable=True)
    holiday_type = Column(String(50), default="National")  # National, Company, Optional
    is_active = Column(Boolean, default=True)

class OfficeLocation(Base):
    """Stores the configurable office GPS location for attendance validation."""
    __tablename__ = "office_location"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), default="Main Office")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_meters = Column(Integer, default=100)  # allowed punch-in/out radius
    is_active = Column(Boolean, default=True)
