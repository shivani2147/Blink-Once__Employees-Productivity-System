from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date, datetime, timedelta
from typing import Optional, List
from database import get_db
from models import (
    User, ProductivityRecord, Attendance, LeaveRequest,
    LeaveBalance, Holiday, OfficeLocation, ProductivityEditHistory
)
from auth import get_current_employee
import math
import json
import os
import shutil

router = APIRouter()

# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

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
    harddisk_number: str = ""
    harddisk_directory: str = ""   # UI label: Folder Name (optional)
    uploaded_to_drive: str = "No"
    drive_link: str = ""
    shoot_type: str
    cameras_used: int
    comments: str = ""

class RecordUpdate(BaseModel):
    client_name: Optional[str] = None
    project_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    deadline_date: Optional[date] = None
    editing_type: Optional[str] = None
    video_duration: Optional[float] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    task_description: Optional[str] = None
    harddisk_number: Optional[str] = None
    harddisk_directory: Optional[str] = None   # UI label: Folder Name
    uploaded_to_drive: Optional[str] = None
    drive_link: Optional[str] = None
    shoot_type: Optional[str] = None
    cameras_used: Optional[int] = None
    comments: Optional[str] = None

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

class PunchRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class PunchOutRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    half_day_reason: Optional[str] = None

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in meters between two GPS coordinates."""
    R = 6_371_000  # Earth radius in meters
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _calc_hours(time_in: str, time_out: str) -> float:
    try:
        t_in  = datetime.strptime(time_in,  "%I:%M %p")
        t_out = datetime.strptime(time_out, "%I:%M %p")
        return round((t_out - t_in).total_seconds() / 3600.0, 2)
    except Exception:
        return 0.0

def _get_office_location(db: Session):
    """Return active office location from DB, or None."""
    return db.query(OfficeLocation).filter(OfficeLocation.is_active == True).first()

def _validate_gps(db: Session, lat: Optional[float], lon: Optional[float]) -> tuple[bool, str]:
    """Returns (is_valid, error_message). If no GPS provided, passes (permissive)."""
    if lat is None or lon is None:
        # GPS not provided — allow without restriction (handles HTTP/dev scenarios)
        return True, ""
    office = _get_office_location(db)
    if not office:
        return True, ""  # No office configured — allow
    dist = _haversine(lat, lon, office.latitude, office.longitude)
    if dist > office.radius_meters:
        return False, (
            f"You are {int(dist)} m away from the office. "
            f"You must be within {office.radius_meters} m to punch in/out."
        )
    return True, ""

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD DATA
# ══════════════════════════════════════════════════════════════════════════════

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
        "address": user.address,
        "email": user.email,
    }

    # --- Today's Attendance ---
    attendance = db.query(Attendance).filter(Attendance.user_id == user.id, Attendance.date == today).first()
    attendance_data = {
        "status": "Not Marked",
        "time_in": None,
        "time_out": None,
        "total_hours": 0,
        "day_type": None,
    }
    if attendance:
        attendance_data["status"] = attendance.status
        attendance_data["time_in"] = attendance.time_in
        attendance_data["time_out"] = attendance.time_out
        attendance_data["day_type"] = attendance.day_type
        if attendance.working_hours is not None:
            attendance_data["total_hours"] = attendance.working_hours
        elif attendance.time_in and attendance.time_out:
            attendance_data["total_hours"] = _calc_hours(attendance.time_in, attendance.time_out)

    # --- Tasks ---
    records = db.query(ProductivityRecord).filter(ProductivityRecord.user_id == user.id).all()
    today_todo = []
    upcoming_deadlines = []
    notifications = []

    stats = {
        "assigned": len(records),
        "completed": 0,
        "pending": 0,
        "upcoming": 0,
        "leaves_taken": 0,
    }

    for r in records:
        if r.status in ("Done", "Completed"):
            stats["completed"] += 1
        else:
            stats["pending"] += 1
            if r.status == "Not Started":
                notifications.append(f"New Task Assigned: {r.client_name} (Priority: {r.priority})")

        task_data = {
            "id": r.id,
            "project_name": r.project_name,
            "client_name": r.client_name,
            "task_description": r.task_description or r.comments,
            "status": r.status,
            "priority": r.priority,
            "deadline_date": r.deadline_date.isoformat() if r.deadline_date else None,
        }

        if r.deadline_date:
            days_remaining = (r.deadline_date - today).days
            task_data["days_remaining"] = days_remaining
            if r.status not in ("Done", "Completed"):
                if days_remaining == 0:
                    today_todo.append(task_data)
                elif days_remaining > 0:
                    upcoming_deadlines.append(task_data)
                    stats["upcoming"] += 1
                    if days_remaining <= 2:
                        notifications.append(f"Deadline approaching for '{r.project_name}' in {days_remaining} day(s)!")
                else:
                    task_data["priority"] = "High"
                    upcoming_deadlines.append(task_data)
                    notifications.append(f"'{r.project_name}' is overdue by {-days_remaining} day(s)!")

    upcoming_deadlines.sort(key=lambda x: x.get("days_remaining", 999))
    if today_todo:
        notifications.append(f"You have {len(today_todo)} task(s) due today.")

    # --- Self Performance Stats ---
    # Attendance percentage (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    att_records = db.query(Attendance).filter(
        Attendance.user_id == user.id,
        Attendance.date >= thirty_days_ago,
        Attendance.date <= today
    ).all()
    total_att_days = len(att_records)
    present_days = len([a for a in att_records if a.status in ("Present", "Late", "Half Day")])
    attendance_pct = round(present_days / total_att_days * 100, 1) if total_att_days > 0 else 100.0

    # On-time completion %
    eval_tasks = [r for r in records if r.status in ("Done", "Completed") and r.deadline_date and r.end_date]
    on_time = len([r for r in eval_tasks if r.end_date <= r.deadline_date])
    on_time_pct = round(on_time / len(eval_tasks) * 100, 1) if eval_tasks else 100.0

    # Monthly performance score
    completion_pct = round(stats["completed"] / stats["assigned"] * 100, 1) if stats["assigned"] > 0 else 100.0
    monthly_score = round(completion_pct * 0.4 + on_time_pct * 0.4 + attendance_pct * 0.2, 1)

    # Performance trend (last 6 months)
    trend_labels = []
    trend_data = []
    for i in range(5, -1, -1):
        m_date = today.replace(day=1) - timedelta(days=i * 28)
        m_start = m_date.replace(day=1)
        if m_date.month == 12:
            m_end = m_date.replace(day=31)
        else:
            m_end = (m_date.replace(month=m_date.month + 1, day=1) - timedelta(days=1))
        m_tasks = [r for r in records if r.date and m_start <= r.date <= m_end]
        m_done = len([r for r in m_tasks if r.status in ("Done", "Completed")])
        m_att = [a for a in att_records if m_start <= a.date <= m_end]
        m_present = len([a for a in m_att if a.status in ("Present", "Late", "Half Day")])
        m_att_pct = (m_present / len(m_att) * 100) if m_att else 100
        m_comp_pct = (m_done / len(m_tasks) * 100) if m_tasks else 100
        m_score = round(m_comp_pct * 0.6 + m_att_pct * 0.4, 1)
        trend_labels.append(m_date.strftime("%b %Y"))
        trend_data.append(m_score)

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
            "status": l.status,
            "days_count": l.days_count,
        })
        if l.status != "Pending" and l.start_date >= today:
            notifications.append(f"Your leave request from {l.start_date.isoformat()} was {l.status.lower()}.")

    # Leave balance
    balance = db.query(LeaveBalance).filter(LeaveBalance.user_id == user.id).first()
    leave_balance = {
        "total": balance.total_leaves if balance else 12,
        "used": balance.used_leaves if balance else 0,
        "remaining": balance.remaining_leaves if balance else 12,
    }

    notifications.append("Welcome to Blink Once EPS! Keep your tasks and records up to date.")

    return {
        "employee": employee_info,
        "attendance": attendance_data,
        "today_todo": today_todo,
        "upcoming_deadlines": upcoming_deadlines,
        "stats": stats,
        "notifications": notifications,
        "leaves": leave_list,
        "leave_balance": leave_balance,
        "performance": {
            "attendance_pct": attendance_pct,
            "on_time_pct": on_time_pct,
            "completion_pct": completion_pct,
            "monthly_score": monthly_score,
        },
        "trend": {
            "labels": trend_labels,
            "data": trend_data,
        }
    }

# ══════════════════════════════════════════════════════════════════════════════
# OFFICE LOCATION (public endpoint — employee needs to know GPS coords)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/office-location")
async def get_office_location(user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    office = _get_office_location(db)
    if not office:
        return {"latitude": None, "longitude": None, "radius_meters": 100, "name": "Not configured"}
    return {
        "latitude": office.latitude,
        "longitude": office.longitude,
        "radius_meters": office.radius_meters,
        "name": office.name,
    }

# ══════════════════════════════════════════════════════════════════════════════
# ATTENDANCE
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/attendance/punch-in")
async def punch_in(req: PunchRequest, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    today = date.today()

    # GPS validation
    valid, err_msg = _validate_gps(db, req.latitude, req.longitude)
    if not valid:
        raise HTTPException(status_code=400, detail=err_msg)

    att = db.query(Attendance).filter(Attendance.user_id == user.id, Attendance.date == today).first()
    if att and att.time_in:
        return {"message": "Already punched in for today.", "already_in": True}

    now_str = datetime.now().strftime("%I:%M %p")
    if att:
        att.time_in = now_str
        att.status = "Present"
        if req.latitude: att.latitude = req.latitude
        if req.longitude: att.longitude = req.longitude
    else:
        att = Attendance(
            user_id=user.id,
            date=today,
            status="Present",
            time_in=now_str,
            latitude=req.latitude,
            longitude=req.longitude,
        )
        db.add(att)
    db.commit()
    return {"message": f"Punched in at {now_str}!", "time_in": now_str}

@router.post("/attendance/punch-out")
async def punch_out(req: PunchOutRequest, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    today = date.today()

    # GPS validation
    valid, err_msg = _validate_gps(db, req.latitude, req.longitude)
    if not valid:
        raise HTTPException(status_code=400, detail=err_msg)

    att = db.query(Attendance).filter(Attendance.user_id == user.id, Attendance.date == today).first()
    if not att or not att.time_in:
        raise HTTPException(status_code=400, detail="You must punch in first!")
    if att.time_out:
        return {"message": "Already punched out for today.", "already_out": True}

    now_str = datetime.now().strftime("%I:%M %p")
    hours = _calc_hours(att.time_in, now_str)

    # Determine day type
    if hours >= 9.0:
        day_type = "Full Day"
    elif hours >= 5.0:
        day_type = "Half Day"
    else:
        day_type = "Short Day"

    # If Half Day, reason is mandatory
    if day_type == "Half Day" and not req.half_day_reason:
        raise HTTPException(
            status_code=400,
            detail="You worked less than a full day (5-9 hrs). Please provide a reason for half-day before punching out."
        )

    att.time_out = now_str
    att.working_hours = hours
    att.day_type = day_type
    att.half_day_reason = req.half_day_reason
    if req.latitude: att.latitude = req.latitude
    if req.longitude: att.longitude = req.longitude

    # Update attendance status based on day type
    if day_type == "Half Day":
        att.status = "Half Day"
    elif day_type == "Short Day":
        att.status = "Short Day"
    # else keep "Present"

    db.commit()
    return {
        "message": f"Punched out at {now_str}. Total: {hours:.1f} hrs ({day_type})",
        "time_out": now_str,
        "working_hours": hours,
        "day_type": day_type,
    }

@router.get("/attendance/history")
async def get_attendance_history(
    user: User = Depends(get_current_employee),
    db: Session = Depends(get_db),
    month: str = ""
):
    query = db.query(Attendance).filter(Attendance.user_id == user.id)
    if month:
        # month format: YYYY-MM
        try:
            yr, mo = map(int, month.split("-"))
            from datetime import date as dt
            start = dt(yr, mo, 1)
            if mo == 12:
                end = dt(yr, 12, 31)
            else:
                end = dt(yr, mo + 1, 1) - timedelta(days=1)
            query = query.filter(Attendance.date >= start, Attendance.date <= end)
        except Exception:
            pass
    records = query.order_by(Attendance.date.desc()).all()
    result = []
    for a in records:
        result.append({
            "id": a.id,
            "date": a.date.isoformat(),
            "status": a.status,
            "time_in": a.time_in,
            "time_out": a.time_out,
            "working_hours": a.working_hours,
            "day_type": a.day_type,
            "half_day_reason": a.half_day_reason,
        })
    # Summary
    present = len([r for r in result if r["status"] in ("Present", "Late")])
    half_days = len([r for r in result if r["status"] == "Half Day"])
    short_days = len([r for r in result if r["status"] == "Short Day"])
    absent = len([r for r in result if r["status"] == "Absent"])
    return {
        "records": result,
        "summary": {
            "present": present,
            "half_day": half_days,
            "short_day": short_days,
            "absent": absent,
            "total": len(result),
        }
    }

# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTIVITY RECORDS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/records")
async def get_records(user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    records = db.query(ProductivityRecord).filter(
        ProductivityRecord.user_id == user.id
    ).order_by(ProductivityRecord.id.desc()).all()
    result = []
    for r in records:
        edit_count = db.query(ProductivityEditHistory).filter(
            ProductivityEditHistory.record_id == r.id
        ).count()
        result.append({
            "id": r.id,
            "date": r.date.isoformat() if r.date else None,
            "client_name": r.client_name,
            "project_name": r.project_name,
            "status": r.status,
            "priority": r.priority,
            "deadline_date": r.deadline_date.isoformat() if r.deadline_date else None,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "cameras_used": r.cameras_used,
            "expected_workload_hours": r.expected_workload_hours or 0,
            "drive_link": r.drive_link or "",
            "comments": r.comments or "",
            "shoot_type": r.shoot_type,
            "editing_type": r.editing_type,
            "video_duration": r.video_duration,
            "harddisk_number": r.harddisk_number,
            "folder_name": r.harddisk_directory or "",   # renamed UI label
            "uploaded_to_drive": r.uploaded_to_drive,
            "task_description": r.task_description or "",
            "edit_count": edit_count,
        })
    return {"records": result}

@router.post("/add")
async def add_record(req: RecordCreate, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
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
        harddisk_directory=req.harddisk_directory,   # "Folder Name"
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

@router.put("/records/{record_id}")
async def edit_record(
    record_id: int,
    req: RecordUpdate,
    user: User = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    record = db.query(ProductivityRecord).filter(
        ProductivityRecord.id == record_id,
        ProductivityRecord.user_id == user.id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    # Capture old values for audit log
    old_vals = {
        "status": record.status,
        "priority": record.priority,
        "drive_link": record.drive_link,
        "comments": record.comments,
        "folder_name": record.harddisk_directory,
        "harddisk_number": record.harddisk_number,
        "task_description": record.task_description,
        "client_name": record.client_name,
        "project_name": record.project_name,
        "editing_type": record.editing_type,
        "video_duration": record.video_duration,
        "cameras_used": record.cameras_used,
        "shoot_type": record.shoot_type,
        "deadline_date": record.deadline_date.isoformat() if record.deadline_date else None,
    }

    # Apply updates
    if req.status is not None:        record.status = req.status
    if req.priority is not None:      record.priority = req.priority
    if req.drive_link is not None:    record.drive_link = req.drive_link
    if req.comments is not None:      record.comments = req.comments
    if req.harddisk_directory is not None: record.harddisk_directory = req.harddisk_directory
    if req.harddisk_number is not None:    record.harddisk_number = req.harddisk_number
    if req.task_description is not None:   record.task_description = req.task_description
    if req.client_name is not None:        record.client_name = req.client_name
    if req.project_name is not None:       record.project_name = req.project_name
    if req.editing_type is not None:       record.editing_type = req.editing_type
    if req.video_duration is not None:     record.video_duration = req.video_duration
    if req.cameras_used is not None:       record.cameras_used = req.cameras_used
    if req.shoot_type is not None:         record.shoot_type = req.shoot_type
    if req.deadline_date is not None:      record.deadline_date = req.deadline_date
    if req.uploaded_to_drive is not None:  record.uploaded_to_drive = (req.uploaded_to_drive == "Yes")
    if req.start_date is not None:         record.start_date = req.start_date
    if req.end_date is not None:           record.end_date = req.end_date

    # Recalculate expected workload if video_duration or cameras changed
    if req.video_duration is not None or req.cameras_used is not None:
        vd = record.video_duration or 0
        cu = record.cameras_used or 1
        record.expected_workload_hours = round(vd * cu * 3, 1)

    new_vals = {
        "status": record.status,
        "priority": record.priority,
        "drive_link": record.drive_link,
        "comments": record.comments,
        "folder_name": record.harddisk_directory,
        "harddisk_number": record.harddisk_number,
        "task_description": record.task_description,
        "client_name": record.client_name,
        "project_name": record.project_name,
        "editing_type": record.editing_type,
        "video_duration": record.video_duration,
        "cameras_used": record.cameras_used,
        "shoot_type": record.shoot_type,
        "deadline_date": record.deadline_date.isoformat() if record.deadline_date else None,
    }

    # Save edit history
    history = ProductivityEditHistory(
        record_id=record_id,
        user_id=user.id,
        edited_at=datetime.utcnow(),
        old_values=json.dumps(old_vals),
        new_values=json.dumps(new_vals),
    )
    db.add(history)
    db.commit()
    return {"message": "Record updated successfully"}

@router.get("/records/{record_id}/history")
async def get_record_history(
    record_id: int,
    user: User = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    record = db.query(ProductivityRecord).filter(
        ProductivityRecord.id == record_id,
        ProductivityRecord.user_id == user.id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    history = db.query(ProductivityEditHistory).filter(
        ProductivityEditHistory.record_id == record_id
    ).order_by(ProductivityEditHistory.edited_at.desc()).all()

    return {
        "record_id": record_id,
        "project_name": record.project_name,
        "history": [
            {
                "id": h.id,
                "edited_at": h.edited_at.isoformat() if h.edited_at else None,
                "old_values": json.loads(h.old_values) if h.old_values else {},
                "new_values": json.loads(h.new_values) if h.new_values else {},
            }
            for h in history
        ]
    }

@router.get("/all-edit-history")
async def get_all_edit_history(user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    """Return all edit history entries for the logged-in employee."""
    history = (
        db.query(ProductivityEditHistory)
        .filter(ProductivityEditHistory.user_id == user.id)
        .order_by(ProductivityEditHistory.edited_at.desc())
        .all()
    )
    result = []
    for h in history:
        rec = db.query(ProductivityRecord).filter(ProductivityRecord.id == h.record_id).first()
        result.append({
            "id": h.id,
            "record_id": h.record_id,
            "project_name": rec.project_name if rec else "—",
            "edited_at": h.edited_at.isoformat() if h.edited_at else None,
            "old_values": json.loads(h.old_values) if h.old_values else {},
            "new_values": json.loads(h.new_values) if h.new_values else {},
        })
    return {"history": result}

# Keep backward-compatible simple PUT
@router.put("/edit/{record_id}")
async def edit_record_compat(record_id: int, req: RecordUpdate, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    return await edit_record(record_id, req, user, db)

@router.put("/task/{record_id}/status")
async def update_task_status(record_id: int, req: StatusUpdate, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    record = db.query(ProductivityRecord).filter(ProductivityRecord.id == record_id, ProductivityRecord.user_id == user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    record.status = req.status
    db.commit()
    return {"message": "Task status updated"}

# ══════════════════════════════════════════════════════════════════════════════
# LEAVE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/leave/balance")
async def get_leave_balance(user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    balance = db.query(LeaveBalance).filter(LeaveBalance.user_id == user.id).first()
    if not balance:
        # Auto-create with 12 annual leaves
        balance = LeaveBalance(user_id=user.id, year=date.today().year, total_leaves=12, used_leaves=0, remaining_leaves=12)
        db.add(balance)
        db.commit()
    return {
        "total": balance.total_leaves,
        "used": balance.used_leaves,
        "remaining": balance.remaining_leaves,
        "year": balance.year,
    }

@router.post("/leave/apply")
async def apply_leave(req: LeaveCreate, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    days = (req.end_date - req.start_date).days + 1
    if days < 1:
        raise HTTPException(status_code=400, detail="End date must be on or after start date.")

    # Check balance for Annual leave type
    if req.leave_type == "Annual":
        balance = db.query(LeaveBalance).filter(LeaveBalance.user_id == user.id).first()
        if balance and balance.remaining_leaves < days:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient annual leave balance. You have {balance.remaining_leaves} days remaining."
            )

    new_leave = LeaveRequest(
        user_id=user.id,
        start_date=req.start_date,
        end_date=req.end_date,
        leave_type=req.leave_type,
        reason=req.reason,
        status="Pending",
        days_count=days,
    )
    db.add(new_leave)
    db.commit()
    return {"message": "Leave application submitted successfully!"}

@router.get("/leave/history")
async def get_leave_history(user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    leaves = db.query(LeaveRequest).filter(
        LeaveRequest.user_id == user.id
    ).order_by(LeaveRequest.start_date.desc()).all()
    result = []
    for l in leaves:
        result.append({
            "id": l.id,
            "leave_type": l.leave_type,
            "start_date": l.start_date.isoformat(),
            "end_date": l.end_date.isoformat(),
            "days_count": l.days_count,
            "reason": l.reason,
            "status": l.status,
        })
    return {"leaves": result}

# ══════════════════════════════════════════════════════════════════════════════
# HOLIDAYS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/holidays")
async def get_holidays(user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    holidays = db.query(Holiday).filter(Holiday.is_active == True).order_by(Holiday.date).all()
    result = []
    today = date.today()
    for h in holidays:
        result.append({
            "id": h.id,
            "name": h.name,
            "date": h.date.isoformat(),
            "day": h.day or h.date.strftime("%A"),
            "description": h.description or "",
            "holiday_type": h.holiday_type,
            "is_past": h.date < today,
        })
    return {"holidays": result}

# ══════════════════════════════════════════════════════════════════════════════
# PROFILE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/profile")
async def get_profile(user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user.id).first()
    return {
        "id": u.id,
        "employee_name": u.employee_name,
        "employee_code": u.employee_code,
        "email": u.email,
        "mobile_number": u.mobile_number,
        "dob": u.dob.isoformat() if u.dob else None,
        "gender": u.gender,
        "address": u.address,
        "emergency_contact": u.emergency_contact,
        "photo_path": u.photo_path,
        "highest_qualification": u.highest_qualification,
        "institution_name": u.institution_name,
        "date_of_joining": u.date_of_joining.isoformat() if u.date_of_joining else None,
        "department": u.department,
        "designation": u.designation,
        "salary_type": u.salary_type,
        "experience": u.experience,
        "skills": u.skills,
        "software_knowledge": u.software_knowledge,
        "camera_skill_level": u.camera_skill_level,
        "resume_path": u.resume_path,
        "aadhaar_front_path": u.aadhaar_front_path,
        "aadhaar_back_path": u.aadhaar_back_path,
        "certificates_path": u.certificates_path,
    }

@router.put("/profile/update")
async def update_profile(req: ProfileUpdate, user: User = Depends(get_current_employee), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user.id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.mobile_number = req.mobile_number
    u.address = req.address
    db.commit()
    return {"message": "Profile updated successfully"}

@router.post("/profile/photo")
async def upload_profile_photo(
    photo: UploadFile = File(...),
    user: User = Depends(get_current_employee),
    db: Session = Depends(get_db)
):
    u = db.query(User).filter(User.id == user.id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    # Build path in employee's folder
    base_folder = os.path.join("static", "Employee_Details")
    if u.employee_code:
        name_clean = "".join(c for c in u.employee_name if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_")
        emp_folder = os.path.join(base_folder, f"{name_clean}_{u.employee_code}")
    else:
        emp_folder = os.path.join(base_folder, f"emp_{u.id}")
    os.makedirs(emp_folder, exist_ok=True)

    ext = os.path.splitext(photo.filename)[1] if photo.filename else ".jpg"
    path = os.path.join(emp_folder, f"passport_photo{ext}")
    with open(path, "wb") as f:
        shutil.copyfileobj(photo.file, f)

    u.photo_path = path.replace("\\", "/")
    db.commit()
    return {"message": "Photo uploaded successfully", "photo_path": u.photo_path}
