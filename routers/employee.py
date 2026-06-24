from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from typing import Optional, List
from database import get_db
from models import User, ProductivityRecord
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

@router.get("/data")
async def get_dashboard_data(user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    records = db.query(ProductivityRecord).filter(ProductivityRecord.user_id == user.id).all()
    # Serialize records
    record_list = []
    for r in records:
        record_list.append({
            "id": r.id,
            "date": r.date.isoformat(),
            "client_name": r.client_name,
            "project_name": r.project_name,
            "status": r.status,
            "deadline_date": r.deadline_date.isoformat() if r.deadline_date else None,
            "cameras_used": r.cameras_used,
            "expected_workload_hours": r.expected_workload_hours,
            "drive_link": r.drive_link,
            "comments": r.comments
        })

    employee_info = {
        "employee_name": user.employee_name,
        "email": user.email,
        "mobile_number": user.mobile_number,
        "dob": user.dob.isoformat() if user.dob else None,
        "gender": user.gender,
        "address": user.address,
        "emergency_contact": user.emergency_contact,
        "highest_qualification": user.highest_qualification,
        "institution_name": user.institution_name,
        "date_of_joining": user.date_of_joining.isoformat() if user.date_of_joining else None,
        "department": user.department,
        "designation": user.designation,
        "salary_type": user.salary_type,
        "salary_value": user.salary_value,
        "experience": user.experience,
        "skills": user.skills,
        "software_knowledge": user.software_knowledge,
        "camera_skill_level": user.camera_skill_level,
        "photo_path": user.photo_path
    }

    return {"records": record_list, "employee": employee_info}

@router.post("/add")
async def add_record(req: RecordCreate, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    base_hours = 10.0
    multiplier = 1.0 + (req.cameras_used - 1) * 0.5
    expected_workload_hours = base_hours * multiplier

    # Estimated completion should consider both editing workload and actual video duration.
    # Use the larger of the two as the basis for completion time.
    video_duration_hours = float(req.video_duration) if req.video_duration is not None else 0.0
    completion_hours = max(expected_workload_hours, video_duration_hours)

    days = int(completion_hours // 8)
    hours = int(completion_hours % 8)

    day_str = f"{days} day{'s' if days != 1 else ''}"
    hour_str = f"{hours} hour{'s' if hours != 1 else ''}"

    if days > 0 and hours > 0:
        estimated_completion_time = f"{day_str} {hour_str}"
    elif days > 0:
        estimated_completion_time = day_str
    else:
        estimated_completion_time = hour_str

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
        harddisk_number=req.harddisk_number,
        harddisk_directory=req.harddisk_directory,
        uploaded_to_drive=True if req.uploaded_to_drive.lower() == 'yes' else False,
        drive_link=req.drive_link,
        shoot_type=req.shoot_type,
        cameras_used=req.cameras_used,
        comments=req.comments,
        expected_workload_hours=expected_workload_hours,
        estimated_completion_time=estimated_completion_time
    )
    
    db.add(new_record)
    db.commit()
    return {"message": "Record added successfully"}

@router.put("/edit/{record_id}")
async def edit_record(record_id: int, req: RecordUpdate, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    record = db.query(ProductivityRecord).filter(ProductivityRecord.id == record_id, ProductivityRecord.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
        
    record.status = req.status
    record.drive_link = req.drive_link
    record.comments = req.comments
    if req.drive_link:
        record.uploaded_to_drive = True
    db.commit()
    return {"message": "Record updated successfully"}
