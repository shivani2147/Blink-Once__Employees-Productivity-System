from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List
from database import get_db
from models import User, ProductivityRecord, Attendance, LeaveRequest
from auth import get_current_employee

router = APIRouter()

class RecordCreate(BaseModel):
    client_name: str
    date: date
    project_name: str
    start_date: date
    end_date: date
    deadline_date: date
    editing_type: str
    video_duration: float
    status: str
    priority: str = "Medium"
    task_description: str = ""
    harddisk_number: str
    harddisk_directory: str
    uploaded_to_drive: str = "No"
    drive_link: str = ""
    shoot_type: str
    cameras_used: int
    comments: str = ""

class RecordUpdate(BaseModel):
    status: str
    drive_link: str = ""
    comments: str = ""

class StatusUpdate(BaseModel):
    status: str

class LeaveCreate(BaseModel):
    leave_type: str
    start_date: date
    end_date: date
    reason: str

class ProfileUpdate(BaseModel):
    mobile_number: str
    address: str
    photo_path: str = ""

@router.get("/records")
async def get_records(user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    records = db.query(ProductivityRecord).filter(ProductivityRecord.user_id == user.id).order_by(ProductivityRecord.id.desc()).all()
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "date": r.date.isoformat() if r.date else None,
            "client_name": r.client_name,
            "project_name": r.project_name,
            "status": r.status,
            "deadline_date": r.deadline_date.isoformat() if r.deadline_date else None,
            "cameras_used": r.cameras_used,
            "expected_workload_hours": r.expected_workload_hours or 0,
            "drive_link": r.drive_link or "",
            "comments": r.comments or "",
            "priority": r.priority,
            "shoot_type": r.shoot_type,
            "editing_type": r.editing_type,
            "video_duration": r.video_duration,
            "harddisk_number": r.harddisk_number,
            "harddisk_directory": r.harddisk_directory,
            "uploaded_to_drive": r.uploaded_to_drive,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
        })
    return {"records": result}

@router.post("/add")
async def add_record(req: RecordCreate, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    # Compute expected workload hours: video_duration * cameras_used * 3 (rough estimate)
    expected_hours = round(req.video_duration * req.cameras_used * 3, 1)
    new_record = ProductivityRecord(
        user_id=user.id,
        employee_name=user.employee_name,
        designation=user.designation,
        client_name=req.client_name,
        date=req.date,
        project_name=req.project_name,
        start_date=req.start_date,
        end_date=req.end_date,
        deadline_date=req.deadline_date,
        editing_type=req.editing_type,
        video_duration=req.video_duration,
        status=req.status,
        priority=req.priority,
        task_description=req.task_description,
        harddisk_number=req.harddisk_number,
        harddisk_directory=req.harddisk_directory,
        uploaded_to_drive=(req.uploaded_to_drive == "Yes"),
        drive_link=req.drive_link,
        shoot_type=req.shoot_type,
        cameras_used=req.cameras_used,
        comments=req.comments,
        expected_workload_hours=expected_hours,
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return {"message": "Record added successfully", "id": new_record.id}

@router.put("/edit/{record_id}")
async def edit_record(record_id: int, req: RecordUpdate, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    record = db.query(ProductivityRecord).filter(ProductivityRecord.id == record_id, ProductivityRecord.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    record.status = req.status
    record.drive_link = req.drive_link
    record.comments = req.comments
    db.commit()
    return {"message": "Record updated successfully"}

@router.get("/data")
async def get_dashboard_data(user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    today = date.today()
    
    # --- Profile Information ---
    employee_info = {
        "employee_name": user.employee_name,
        "employee_code": user.employee_code,
        "department": user.department,
        "designation": user.designation,
        "date_of_joining": user.date_of_joining.isoformat() if user.date_of_joining else None,
        "photo_path": user.photo_path,
        "mobile_number": user.mobile_number,
        "address": user.address
    }
    
    # --- Attendance logic ---
    attendance = db.query(Attendance).filter(Attendance.user_id == user.id, Attendance.date == today).first()
    attendance_data = {
        "status": "Absent",
        "time_in": None,
        "time_out": None,
        "total_hours": 0
    }
    if attendance:
        attendance_data["status"] = attendance.status
        attendance_data["time_in"] = attendance.time_in
        attendance_data["time_out"] = attendance.time_out
        
        # Calculate total working hours
        if attendance.time_in and attendance.time_out:
            t_in = datetime.strptime(attendance.time_in, "%I:%M %p")
            t_out = datetime.strptime(attendance.time_out, "%I:%M %p")
            diff = t_out - t_in
            attendance_data["total_hours"] = round(diff.total_seconds() / 3600.0, 1)

    # --- Tasks (Productivity Records) ---
    records = db.query(ProductivityRecord).filter(ProductivityRecord.user_id == user.id).all()
    today_todo = []
    upcoming_deadlines = []
    
    stats = {
        "assigned": len(records),
        "completed": 0,
        "pending": 0,
        "upcoming": 0,
        "leaves_taken": 0
    }

    notifications = []

    for r in records:
        if r.status == "Completed":
            stats["completed"] += 1
        else:
            stats["pending"] += 1
        
        task_data = {
            "id": r.id,
            "project_name": r.project_name,
            "client_name": r.client_name,
            "task_description": r.task_description or r.comments,
            "status": r.status,
            "priority": r.priority,
            "deadline_date": r.deadline_date.isoformat() if r.deadline_date else None
        }

        if r.deadline_date:
            days_remaining = (r.deadline_date - today).days
            task_data["days_remaining"] = days_remaining
            
            if r.status != "Completed":
                if days_remaining == 0:
                    today_todo.append(task_data)
                elif days_remaining > 0:
                    upcoming_deadlines.append(task_data)
                    stats["upcoming"] += 1
                    if days_remaining <= 2:
                        notifications.append(f"Upcoming deadline for {r.project_name} in {days_remaining} days!")
                else:
                    task_data["priority"] = "High" # overdue
                    upcoming_deadlines.append(task_data)

    # Sort upcoming by days remaining
    upcoming_deadlines.sort(key=lambda x: x.get("days_remaining", 999))
    
    # Check for new tasks (created recently)
    # Simple heuristic: if any task is 'Pending' and deadline is far out, notify.
    if len(today_todo) > 0:
        notifications.append(f"You have {len(today_todo)} tasks due today.")

    # --- Leave History ---
    leaves = db.query(LeaveRequest).filter(LeaveRequest.user_id == user.id).order_by(LeaveRequest.start_date.desc()).all()
    leave_list = []
    for l in leaves:
        if l.status == "Approved":
            stats["leaves_taken"] += 1
        leave_list.append({
            "id": l.id,
            "leave_type": l.leave_type,
            "start_date": l.start_date.isoformat(),
            "end_date": l.end_date.isoformat(),
            "reason": l.reason,
            "status": l.status
        })
        if l.status != "Pending" and l.start_date >= today:
            notifications.append(f"Your leave request starting {l.start_date.isoformat()} was {l.status.lower()}.")

    # Add general announcement
    notifications.append("Welcome to the new Blink Once Dashboard! Keep your tasks updated.")

    return {
        "employee": employee_info,
        "attendance": attendance_data,
        "today_todo": today_todo,
        "upcoming_deadlines": upcoming_deadlines,
        "stats": stats,
        "notifications": notifications,
        "leaves": leave_list
    }

@router.post("/attendance/punch-in")
async def punch_in(user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    today = date.today()
    att = db.query(Attendance).filter(Attendance.user_id == user.id, Attendance.date == today).first()
    if att:
        if att.time_in:
            return {"message": "Already punched in for today."}
        else:
            att.time_in = datetime.now().strftime("%I:%M %p")
            att.status = "Present"
            db.commit()
    else:
        new_att = Attendance(
            user_id=user.id,
            date=today,
            status="Present",
            time_in=datetime.now().strftime("%I:%M %p")
        )
        db.add(new_att)
        db.commit()
    return {"message": "Punched in successfully!"}

@router.post("/attendance/punch-out")
async def punch_out(user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    today = date.today()
    att = db.query(Attendance).filter(Attendance.user_id == user.id, Attendance.date == today).first()
    if not att or not att.time_in:
        raise HTTPException(status_code=400, detail="You must punch in first!")
    
    if att.time_out:
        return {"message": "Already punched out for today."}
        
    att.time_out = datetime.now().strftime("%I:%M %p")
    db.commit()
    return {"message": "Punched out successfully!"}

@router.put("/task/{record_id}/status")
async def update_task_status(record_id: int, req: StatusUpdate, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    record = db.query(ProductivityRecord).filter(ProductivityRecord.id == record_id, ProductivityRecord.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    record.status = req.status
    db.commit()
    return {"message": "Task status updated"}

@router.post("/leave/apply")
async def apply_leave(req: LeaveCreate, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    new_leave = LeaveRequest(
        user_id=user.id,
        start_date=req.start_date,
        end_date=req.end_date,
        leave_type=req.leave_type,
        reason=req.reason,
        status="Pending"
    )
    db.add(new_leave)
    db.commit()
    return {"message": "Leave application submitted!"}

@router.put("/profile/update")
async def update_profile(req: ProfileUpdate, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    user_record = db.query(User).filter(User.id == user.id).first()
    if not user_record:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_record.mobile_number = req.mobile_number
    user_record.address = req.address
    if req.photo_path:
        user_record.photo_path = req.photo_path
        
    db.commit()
    return {"message": "Profile updated successfully"}
