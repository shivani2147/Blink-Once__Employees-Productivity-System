from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from models import User, ProductivityRecord, Attendance, LeaveRequest, LeaveBalance, Holiday, OfficeLocation, ProductivityEditHistory, Notification
from sqlalchemy import or_
import json as _json
import json
from auth import get_current_admin, get_password_hash
from fastapi import UploadFile, File, Form
import shutil, os, io, csv
import datetime
import random
import string

router = APIRouter()

class AdminSettingsUpdate(BaseModel):
    username: str
    email: Optional[str] = None
    verification_code: Optional[str] = None
    password: Optional[str] = None
    confirm_password: Optional[str] = None

verification_codes = {}

class SendCodeRequest(BaseModel):
    email: str

@router.post("/send-verification-code")
async def send_verification_code(req: SendCodeRequest, user: User = Depends(get_current_admin)):
    code = ''.join(random.choices(string.digits, k=6))
    verification_codes[req.email] = code
    print(f"\n--- MOCK EMAIL ---")
    print(f"To: {req.email}")
    print(f"Subject: Your Verification Code")
    print(f"Body: Your verification code is: {code}")
    print(f"------------------\n")
    return {"message": "Verification code sent to email (mocked in console)"}

@router.get("/data")
async def get_admin_dashboard_data(
    user: User = Depends(get_current_admin), 
    db: Session = Depends(get_db),
    employee_filter: str = "",
    client_filter: str = "",
    project_filter: str = "",
    status_filter: str = "",
    year: Optional[int] = None,
    month: Optional[int] = None,
    day: Optional[int] = None,
):
    query = db.query(ProductivityRecord)
    
    if employee_filter:
        query = query.filter(ProductivityRecord.employee_name.ilike(f"%{employee_filter}%"))
    if client_filter:
        query = query.filter(ProductivityRecord.client_name.ilike(f"%{client_filter}%"))
    if project_filter:
        query = query.filter(ProductivityRecord.project_name.ilike(f"%{project_filter}%"))
    if status_filter:
        query = query.filter(ProductivityRecord.status == status_filter)
    
    records = query.all()
    if year is not None:
        records = [r for r in records if r.date and r.date.year == year]
    if month is not None:
        records = [r for r in records if r.date and r.date.month == month]
    if day is not None:
        records = [r for r in records if r.date and r.date.day == day]
    employees = db.query(User).filter(User.role == "Employee").all()
    
    total_employees = len(employees)
    total_projects = len(records)
    completed_projects = len([r for r in records if r.status == "Done"])
    ongoing_projects = len([r for r in records if r.status == "Ongoing"])
    hold_projects = len([r for r in records if r.status == "Hold"])
    
    emp_days_taken = {}
    record_list = []
    
    for r in records:
        if r.employee_name not in emp_days_taken:
            emp_days_taken[r.employee_name] = 0
            
        # Calculate days taken based on number of cameras (use README formula)
        base_hours = 10.0
        multiplier = 1.0 + (r.cameras_used - 1) * 0.5
        expected_workload_hours = base_hours * multiplier

        # Consider video duration when calculating completion days/time
        video_duration_hours = float(r.video_duration) if r.video_duration is not None else 0.0
        completion_hours = max(expected_workload_hours, video_duration_hours)
        days_taken = completion_hours / 8.0

        emp_days_taken[r.employee_name] += days_taken

        # Recompute a readable estimated completion time to ensure admin view matches the calculation
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

        record_list.append({
            "id": r.id,
            "employee_name": r.employee_name,
            "designation": r.designation,
            "date": r.date.isoformat(),
            "client_name": r.client_name,
            "project_name": r.project_name,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "deadline_date": r.deadline_date.isoformat() if r.deadline_date else None,
            "video_duration": r.video_duration,
            "status": r.status,
            "cameras_used": r.cameras_used,
            "expected_workload_hours": expected_workload_hours,
            "shoot_type": r.shoot_type,
            "uploaded_to_drive": r.uploaded_to_drive,
            "harddisk_number": r.harddisk_number,
            "harddisk_directory": r.harddisk_directory,
            "drive_link": r.drive_link,
            "comments": r.comments,
            "estimated_completion_time": estimated_completion_time
        })
            
    analytics_data = {
        "labels": list(emp_days_taken.keys()),
        "data": [round(days) for days in emp_days_taken.values()]
    }
    
    return {
        "stats": {
            "total_employees": total_employees,
            "total_projects": total_projects,
            "completed_projects": completed_projects,
            "ongoing_projects": ongoing_projects,
            "hold_projects": hold_projects
        },
        "analytics": analytics_data,
        "records": record_list
    }


@router.get("/notifications")
async def get_admin_notifications(user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    """Generate and return admin notifications; persist them so read/unread can be tracked."""
    today = datetime.date.today()
    week_ago = today - datetime.timedelta(days=7)
    now = datetime.datetime.utcnow()

    def _exists(meta_key, ref_id):
        like_str = f'%"{meta_key}": "{ref_id}"%'
        return db.query(Notification).filter(Notification.meta_data.like(like_str)).first()

    def _create_if_missing(type_, message, priority, metadata, created_at=None):
        ref_id = metadata.get('ref_id')
        if ref_id and _exists('ref_id', ref_id):
            return
        n = Notification(
            type=type_,
            message=message,
            priority=priority,
            meta_data=_json.dumps(metadata),
            created_at=created_at or datetime.datetime.utcnow()
        )
        db.add(n)

    # 1) Leave requests
    lrs = db.query(LeaveRequest).filter(or_(LeaveRequest.start_date >= week_ago, LeaveRequest.start_date == today)).all()
    for lr in lrs:
        user_obj = db.query(User).filter(User.id == lr.user_id).first()
        who = user_obj.employee_name if user_obj else 'Unknown'
        
        msg = f"{who} requested {lr.leave_type} from {lr.start_date.isoformat()} to {lr.end_date.isoformat()}."
        title = "New Leave Request"
        priority = "Medium"
        if lr.status == 'Approved':
            title = "Leave Approved"
            msg = f"{who}'s {lr.leave_type} has been approved."
            priority = "Low"
        elif lr.status == 'Rejected':
            title = "Leave Rejected"
            msg = f"{who}'s {lr.leave_type} request has been rejected."
            priority = "High"
        elif lr.start_date == today + datetime.timedelta(days=1) and lr.status == 'Approved':
            title = "Leave Starts Tomorrow"
            msg = f"{who}'s approved leave begins tomorrow."
            priority = "High"
            
        metadata = {'ref_id': f'leave_{lr.id}_{lr.status}', 'title': title, 'employee_name': who, 'project_name': ''}
        _create_if_missing('leave', msg, priority, metadata)

    # 2) Task Notifications
    tasks = db.query(ProductivityRecord).filter(or_(ProductivityRecord.deadline_date <= today, ProductivityRecord.status == 'Done')).all()
    for t in tasks:
        if t.status != 'Done' and t.deadline_date < today:
            title = "Task Overdue"
            msg = f"{t.employee_name} has not completed \"{t.project_name}\" which was due on {t.deadline_date.isoformat()}."
            priority = "High"
            _create_if_missing('task', msg, priority, {'ref_id': f'overdue_{t.id}', 'title': title, 'employee_name': t.employee_name, 'project_name': t.project_name})
        elif t.status != 'Done' and t.deadline_date == today:
            title = "Deadline Today"
            msg = f"{t.employee_name}'s task \"{t.project_name}\" is due today."
            priority = "High"
            _create_if_missing('task', msg, priority, {'ref_id': f'deadline_{t.id}', 'title': title, 'employee_name': t.employee_name, 'project_name': t.project_name})
        elif t.status == 'Done' and t.updated_at and t.updated_at.date() >= week_ago:
            title = "Task Completed"
            msg = f"{t.employee_name} completed \"{t.project_name}\" successfully."
            priority = "Low"
            _create_if_missing('task', msg, priority, {'ref_id': f'completed_{t.id}', 'title': title, 'employee_name': t.employee_name, 'project_name': t.project_name}, created_at=t.updated_at)

    # 3) Productivity record updates
    edits = db.query(ProductivityEditHistory).filter(ProductivityEditHistory.edited_at >= datetime.datetime.utcnow() - datetime.timedelta(days=7)).order_by(ProductivityEditHistory.edited_at.desc()).all()
    for e in edits:
        rec = db.query(ProductivityRecord).filter(ProductivityRecord.id == e.record_id).first()
        who = db.query(User).filter(User.id == e.user_id).first()
        who_name = who.employee_name if who else 'System'
        proj_name = rec.project_name if rec else str(e.record_id)
        
        try:
            newv = _json.loads(e.new_values or "{}")
        except Exception:
            newv = {}
            
        doc_fields = ['drive_link', 'harddisk_directory', 'resume_path', 'aadhaar_front_path', 'aadhaar_back_path', 'certificates_path']
        if any(f in newv for f in doc_fields):
            title = "Documents Uploaded"
            msg = f"{who_name} uploaded documents for \"{proj_name}\"."
            _create_if_missing('employee', msg, 'Low', {'ref_id': f'doc_{e.id}', 'title': title, 'employee_name': who_name, 'project_name': proj_name}, created_at=e.edited_at)
        else:
            title = "Productivity Record Updated"
            msg = f"{who_name} updated the productivity record for \"{proj_name}\"."
            _create_if_missing('productivity', msg, 'Medium', {'ref_id': f'edit_{e.id}', 'title': title, 'employee_name': who_name, 'project_name': proj_name}, created_at=e.edited_at)

    # 4) New employee additions
    new_emps = db.query(User).filter(User.role == 'Employee', User.date_of_joining != None, User.date_of_joining >= week_ago).all()
    for ne in new_emps:
        title = "New Employee Added"
        msg = f"{ne.employee_name} has joined as {ne.position or 'Employee'}."
        _create_if_missing('employee', msg, 'Low', {'ref_id': f'emp_{ne.id}', 'title': title, 'employee_name': ne.employee_name, 'project_name': ''}, created_at=ne.date_of_joining)

    # 5) Upcoming holidays
    holidays = db.query(Holiday).filter(Holiday.date >= today, Holiday.date <= today + datetime.timedelta(days=7)).all()
    for h in holidays:
        title = "Upcoming Holiday"
        msg = f"Upcoming holiday is {h.name} on {h.date.isoformat()}."
        if h.date == today + datetime.timedelta(days=1):
            msg = f"Tomorrow is {h.name}."
        _create_if_missing('holiday', msg, 'Low', {'ref_id': f'hol_{h.id}', 'title': title, 'employee_name': '', 'project_name': ''})

    # 6) Attendance Notifications (Today's exceptions)
    today_att = db.query(Attendance).filter(Attendance.date == today).all()
    att_by_user = {a.user_id: a for a in today_att}
    all_emps = db.query(User).filter(User.role == 'Employee').all()
    
    shift_start = datetime.datetime.combine(today, datetime.time(9, 0))
    now_local = datetime.datetime.now()

    for emp in all_emps:
        att = att_by_user.get(emp.id)
        if not att:
            if now_local.hour >= 11:
                title = "Missed Punch-in"
                msg = f"{emp.employee_name} has not punched in today."
                _create_if_missing('attendance', msg, 'High', {'ref_id': f'nopunch_{emp.id}_{today.isoformat()}', 'title': title, 'employee_name': emp.employee_name, 'project_name': ''})
        else:
            if att.time_in:
                try:
                    t_in = datetime.datetime.strptime(att.time_in, "%I:%M %p").time()
                    punch_in_dt = datetime.datetime.combine(today, t_in)
                    if punch_in_dt > shift_start + datetime.timedelta(minutes=15):
                        late_diff = punch_in_dt - shift_start
                        late_mins = int(late_diff.total_seconds() / 60)
                        title = "Late Arrival"
                        msg = f"{emp.employee_name} arrived late by {late_mins} minutes."
                        _create_if_missing('attendance', msg, 'Medium', {'ref_id': f'late_{emp.id}_{today.isoformat()}', 'title': title, 'employee_name': emp.employee_name, 'project_name': ''}, created_at=punch_in_dt)
                    else:
                        title = "Punched In"
                        msg = f"{emp.employee_name} punched in at {att.time_in}."
                        _create_if_missing('attendance', msg, 'Low', {'ref_id': f'punchin_{emp.id}_{today.isoformat()}', 'title': title, 'employee_name': emp.employee_name, 'project_name': ''}, created_at=punch_in_dt)
                except ValueError:
                    pass
            
            if att.time_out and getattr(att, 'day_type', None) == 'Half Day':
                try:
                    t_out = datetime.datetime.strptime(att.time_out, "%I:%M %p").time()
                    punch_out_dt = datetime.datetime.combine(today, t_out)
                    title = "Half-Day Punch Out"
                    msg = f"{emp.employee_name} punched out with Half-Day attendance."
                    _create_if_missing('attendance', msg, 'Medium', {'ref_id': f'halfday_{emp.id}_{today.isoformat()}', 'title': title, 'employee_name': emp.employee_name, 'project_name': ''}, created_at=punch_out_dt)
                except ValueError:
                    pass

    db.commit()

    notes = db.query(Notification).order_by(Notification.created_at.desc()).all()
    out = []
    for n in notes:
        out.append({
            'id': n.id,
            'message': n.message,
            'priority': n.priority,
            'is_read': n.is_read
        })
    return {'notifications': out}


class MarkReq(BaseModel):
    id: int
    is_read: bool


@router.post('/notifications/mark')
async def mark_notification(req: MarkReq, user: User = Depends(get_current_admin), db: Session = Depends(get_db)):
    n = db.query(Notification).filter(Notification.id == req.id).first()
    if not n:
        raise HTTPException(status_code=404, detail='Notification not found')
    n.is_read = bool(req.is_read)
    db.commit()
    return {'message': 'Updated'}

@router.put("/settings")
async def update_admin_settings(
    req: AdminSettingsUpdate,
    request: Request,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    if req.password and req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    user.username = req.username
    
    if req.email:
        if req.verification_code != verification_codes.get(req.email):
            raise HTTPException(status_code=400, detail="Invalid or expired verification code")
        user.email = req.email
        if req.email in verification_codes:
            del verification_codes[req.email]
            
    if req.password:
        user.password_hash = get_password_hash(req.password)
    db.commit()
    
    request.session.clear()
    return {"message": "Credentials updated successfully. Please log in again."}


@router.post("/add-employee")
async def add_employee(
    request: Request,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    full_name: str = Form(...),
    email: str = Form(...),
    mobile_number: str = Form(...),
    dob: str = Form(...),
    gender: str = Form(...),
    address: str = Form(...),
    emergency_contact: Optional[str] = Form(None),
    highest_qualification: Optional[str] = Form(None),
    institution_name: Optional[str] = Form(None),
    date_of_joining: Optional[str] = Form(None),
    department: Optional[List[str]] = Form(None),
    designation: Optional[List[str]] = Form(None),
    salary_type: Optional[str] = Form(None),
    salary_amount: Optional[float] = Form(None),
    experience: Optional[str] = Form(None),
    skills: Optional[str] = Form(None),
    software_knowledge: Optional[str] = Form(None),
    camera_skill_level: Optional[str] = Form(None),
    editing_type: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    resume: Optional[UploadFile] = File(None),
    aadhaar_front: Optional[UploadFile] = File(None),
    aadhaar_back: Optional[UploadFile] = File(None),
    certificates: Optional[UploadFile] = File(None),
):
    # Check if email is already registered
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return JSONResponse(
            status_code=400, 
            content={"message": f"Email '{email}' is already registered to another employee. Please use a different email."}
        )

    # generate employee code
    last = db.query(User).order_by(User.id.desc()).first()
    if last and last.employee_code and last.employee_code.startswith('EMP'):
        try:
            num = int(last.employee_code.replace('EMP','')) + 1
        except:
            num = last.id + 1
    else:
        num = (last.id + 1) if last else 1
    employee_code = f"EMP{num:03d}"

    # prepare file paths: create main Employee_Details folder and per-employee subfolder (full_name_empID)
    base_folder = os.path.join('static', 'Employee_Details')
    def sanitize_name(name: str) -> str:
        if not name:
            return 'unknown'
        # allow alnum, space, dash, underscore; replace spaces with underscore
        cleaned = ''.join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        return cleaned.replace(' ', '_') or 'employee'

    emp_folder_name = f"{sanitize_name(full_name)}_{employee_code}"
    emp_folder = os.path.join(base_folder, emp_folder_name)
    os.makedirs(emp_folder, exist_ok=True)

    def save_file(file: UploadFile, folder: str, custom_name: str):
        if not file or not getattr(file, "filename", None):
            return None
        # Extract file extension
        file_ext = os.path.splitext(file.filename)[1]
        filename = f"{custom_name}{file_ext}"
        path = os.path.join(folder, filename)
        with open(path, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        return path.replace('\\', '/')

    photo_path = save_file(photo, emp_folder, 'passport_photo')
    resume_path = save_file(resume, emp_folder, 'resume')
    aadhaar_front_path = save_file(aadhaar_front, emp_folder, 'front_aadhar_card')
    aadhaar_back_path = save_file(aadhaar_back, emp_folder, 'back_aadhar_card')
    certificates_path = save_file(certificates, emp_folder, 'certificates')

    # Create user with email registered but no real password yet.
    # Use a temporary placeholder username and empty password_hash to remain compatible
    # with older DB schemas that still enforced NOT NULL constraints.
    new_user = User(
        employee_name=full_name,
        employee_code=employee_code,
        email=email,
        username=f'pending_{employee_code}',
        password_hash='',
        role='Employee',
        mobile_number=mobile_number,
        dob=dob,
        gender=gender,
        address=address,
        emergency_contact=emergency_contact,
        photo_path=photo_path,
        
        highest_qualification=highest_qualification,
        institution_name=institution_name,
        marksheet_path=None,
        date_of_joining=date_of_joining,
        department=','.join(department) if department else None,
        salary_type=salary_type,
        salary_amount=salary_amount,
        experience=experience,
        skills=skills,
        software_knowledge=software_knowledge,
        camera_skill_level=camera_skill_level,
        designation=','.join(designation) if designation else designation,
        resume_path=resume_path,
        aadhaar_front_path=aadhaar_front_path,
        aadhaar_back_path=aadhaar_back_path,
        certificates_path=certificates_path
    )

    db.add(new_user)
    db.commit()
    return {"message": "Employee created", "employee_code": employee_code}


@router.get("/employees")
async def get_all_employees(
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Fetch all employees with full details for View Employee page."""
    employees = db.query(User).filter(User.role == "Employee").all()
    
    result = []
    for emp in employees:
        result.append({
            "id": emp.id,
            "employee_code": emp.employee_code,
            "employee_name": emp.employee_name,
            "email": emp.email,
            "mobile_number": emp.mobile_number,
            "dob": emp.dob.isoformat() if emp.dob else None,
            "gender": emp.gender,
            "address": emp.address,
            "emergency_contact": emp.emergency_contact,
            "photo_path": emp.photo_path,
            "highest_qualification": emp.highest_qualification,
            "institution_name": emp.institution_name,
            "date_of_joining": emp.date_of_joining.isoformat() if emp.date_of_joining else None,
            "department": emp.department,
            "designation": emp.designation,
            "salary_type": emp.salary_type,
            "salary_value": emp.salary_value,
            "experience": emp.experience,
            "skills": emp.skills,
            "software_knowledge": emp.software_knowledge,
            "camera_skill_level": emp.camera_skill_level,
            "resume_path": emp.resume_path,
            "aadhaar_front_path": emp.aadhaar_front_path,
            "aadhaar_back_path": emp.aadhaar_back_path,
            "certificates_path": emp.certificates_path
        })
    
    return {"employees": result}

@router.get("/performance-data")
async def get_performance_data(
    user: User = Depends(get_current_admin), 
    db: Session = Depends(get_db),
    start_date: str = "",
    end_date: str = "",
    department: str = "",
    designation: str = "",
    employee_id: str = "",
    year: Optional[int] = None,
    month: Optional[int] = None,
    day: Optional[int] = None,
):
    today = datetime.date.today()
    
    # Base queries
    emp_query = db.query(User).filter(User.role == "Employee")
    if department:
        emp_query = emp_query.filter(User.department.ilike(f"%{department}%"))
    if designation:
        emp_query = emp_query.filter(User.designation.ilike(f"%{designation}%"))
    if employee_id:
        emp_query = emp_query.filter(User.id == int(employee_id))
        
    employees = emp_query.all()
    emp_ids = [e.id for e in employees]
    
    # Total Employees
    total_employees = len(employees)
    
    # Attendance Today
    today_attendance = db.query(Attendance).filter(Attendance.date == today, Attendance.user_id.in_(emp_ids)).all()
    if year is not None:
        today_attendance = [a for a in today_attendance if a.date and a.date.year == year]
    if month is not None:
        today_attendance = [a for a in today_attendance if a.date and a.date.month == month]
    if day is not None:
        today_attendance = [a for a in today_attendance if a.date and a.date.day == day]
    present_today = len([a for a in today_attendance if a.status == "Present"])
    late_today = len([a for a in today_attendance if a.status == "Late"])
    absent_today = len([a for a in today_attendance if a.status == "Absent"])
    
    # Task queries
    tasks_query = db.query(ProductivityRecord).filter(ProductivityRecord.user_id.in_(emp_ids))
    if start_date and end_date:
        tasks_query = tasks_query.filter(ProductivityRecord.date >= start_date, ProductivityRecord.date <= end_date)
    elif year is not None or month is not None or day is not None:
        if year is not None:
            tasks_query = tasks_query.filter(ProductivityRecord.date != None)
        if month is not None:
            tasks_query = tasks_query.filter(ProductivityRecord.date != None)
        if day is not None:
            tasks_query = tasks_query.filter(ProductivityRecord.date != None)
    
    all_tasks = tasks_query.all()
    if year is not None:
        all_tasks = [t for t in all_tasks if t.date and t.date.year == year]
    if month is not None:
        all_tasks = [t for t in all_tasks if t.date and t.date.month == month]
    if day is not None:
        all_tasks = [t for t in all_tasks if t.date and t.date.day == day]
    
    tasks_assigned_today = len([t for t in all_tasks if t.date == today])
    tasks_completed_today = len([t for t in all_tasks if t.status == "Done" and t.date == today])
    tasks_due_today = len([t for t in all_tasks if t.deadline_date == today])
    
    total_assigned = len(all_tasks)
    completed_tasks = len([t for t in all_tasks if t.status == "Done"])
    pending_tasks = len([t for t in all_tasks if t.status in ["Ongoing", "Hold", "Not Started"]])
    
    overdue_tasks = len([t for t in all_tasks if t.status != "Done" and t.deadline_date and t.deadline_date < today])
    
    # On-Time Completion Rate (Overall)
    on_time_tasks = len([t for t in all_tasks if t.status == "Done" and t.deadline_date and t.end_date and t.end_date <= t.deadline_date])
    evaluable_tasks = len([t for t in all_tasks if t.status == "Done" and t.deadline_date and t.end_date])
    overall_on_time_rate = (on_time_tasks / evaluable_tasks * 100) if evaluable_tasks > 0 else 100
    
    # Leave Requests
    pending_leaves = db.query(LeaveRequest).filter(LeaveRequest.status == "Pending", LeaveRequest.user_id.in_(emp_ids)).count()
    
    # Per-employee calculations
    employee_performance = []
    
    # Attendance query for the period
    try:
        sd = datetime.date.fromisoformat(start_date) if start_date else today - datetime.timedelta(days=30)
        ed = datetime.date.fromisoformat(end_date) if end_date else today
    except:
        sd = today - datetime.timedelta(days=30)
        ed = today
        
    att_records = db.query(Attendance).filter(Attendance.date >= sd, Attendance.date <= ed, Attendance.user_id.in_(emp_ids)).all()
    if year is not None:
        att_records = [a for a in att_records if a.date and a.date.year == year]
    if month is not None:
        att_records = [a for a in att_records if a.date and a.date.month == month]
    if day is not None:
        att_records = [a for a in att_records if a.date and a.date.day == day]
    
    for emp in employees:
        emp_tasks = [t for t in all_tasks if t.user_id == emp.id]
        assigned = len(emp_tasks)
        completed = len([t for t in emp_tasks if t.status == "Done"])
        pending = assigned - completed
        
        emp_eval_tasks = [t for t in emp_tasks if t.status == "Done" and t.deadline_date and t.end_date]
        emp_on_time = len([t for t in emp_eval_tasks if t.end_date <= t.deadline_date])
        on_time_perc = (emp_on_time / len(emp_eval_tasks) * 100) if len(emp_eval_tasks) > 0 else 100
        if assigned == 0:
            on_time_perc = 100
            
        emp_att = [a for a in att_records if a.user_id == emp.id]
        total_days = len(emp_att)
        present_days = len([a for a in emp_att if a.status in ["Present", "Late"]])
        attendance_perc = (present_days / total_days * 100) if total_days > 0 else 100
        
        # Simple score calculation
        completion_perc = (completed / assigned * 100) if assigned > 0 else 100
        score = (completion_perc * 0.4) + (on_time_perc * 0.4) + (attendance_perc * 0.2)
        
        if score >= 85:
            status = "Excellent"
        elif score >= 70:
            status = "Good"
        elif score >= 50:
            status = "Average"
        else:
            status = "Needs Attention"
            
        employee_performance.append({
            "id": emp.id,
            "name": emp.employee_name,
            "employee_code": emp.employee_code,
            "department": emp.department or "-",
            "designation": emp.designation or "-",
            "assigned": assigned,
            "completed": completed,
            "pending": pending,
            "on_time_perc": round(on_time_perc, 1),
            "attendance_perc": round(attendance_perc, 1),
            "score": round(score, 1),
            "status": status
        })
        
    employee_performance.sort(key=lambda x: x["score"], reverse=True)
    
    best_performer = employee_performance[0] if employee_performance else None
    
    top_by_tasks = sorted(employee_performance, key=lambda x: x["completed"], reverse=True)[:5]
    top_by_ontime = sorted(employee_performance, key=lambda x: x["on_time_perc"], reverse=True)[:5]
    top_by_attendance = sorted(employee_performance, key=lambda x: x["attendance_perc"], reverse=True)[:5]
    
    needs_attention = [e for e in employee_performance if e["status"] == "Needs Attention"]
    high_pending = sorted(employee_performance, key=lambda x: x["pending"], reverse=True)[:5]
    
    chart_tasks_names = [e["name"] for e in employee_performance[:10]]
    chart_tasks_data = [e["completed"] for e in employee_performance[:10]]

    # ── Performance Trend (last 6 months, per employee) ──────────────────────
    # Fetch ALL tasks and attendance for all matching employees across last 6 months
    trend_start = (today.replace(day=1) - datetime.timedelta(days=5 * 28)).replace(day=1)
    all_trend_tasks = db.query(ProductivityRecord).filter(
        ProductivityRecord.user_id.in_(emp_ids),
        ProductivityRecord.date >= trend_start
    ).all()
    all_trend_att = db.query(Attendance).filter(
        Attendance.user_id.in_(emp_ids),
        Attendance.date >= trend_start
    ).all()

    # Build 6-month labels
    trend_month_labels = []
    trend_month_ranges = []
    for i in range(5, -1, -1):
        m_date = today.replace(day=1) - datetime.timedelta(days=i * 28)
        m_start = m_date.replace(day=1)
        if m_date.month == 12:
            m_end = m_date.replace(day=31)
        else:
            m_end = (m_date.replace(month=m_date.month + 1, day=1) - datetime.timedelta(days=1))
        trend_month_labels.append(m_date.strftime("%b %Y"))
        trend_month_ranges.append((m_start, m_end))

    # Per-employee trend datasets
    trend_datasets = []
    # Palette of distinct colors for multiple employees
    palette = [
        "#6366f1", "#f59e0b", "#10b981", "#ef4444", "#3b82f6",
        "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#84cc16"
    ]
    for idx, emp in enumerate(employees):
        emp_trend_data = []
        for (m_start, m_end) in trend_month_ranges:
            m_tasks = [t for t in all_trend_tasks if t.user_id == emp.id and t.date and m_start <= t.date <= m_end]
            m_done  = len([t for t in m_tasks if t.status in ("Done", "Completed")])
            m_att   = [a for a in all_trend_att if a.user_id == emp.id and m_start <= a.date <= m_end]
            m_present = len([a for a in m_att if a.status in ("Present", "Late", "Half Day")])
            m_att_pct  = (m_present / len(m_att) * 100) if m_att else 100
            m_comp_pct = (m_done / len(m_tasks) * 100) if m_tasks else 100
            m_score = round(m_comp_pct * 0.6 + m_att_pct * 0.4, 1)
            emp_trend_data.append(m_score)
        color = palette[idx % len(palette)]
        trend_datasets.append({
            "emp_id": emp.id,
            "name": emp.employee_name,
            "data": emp_trend_data,
            "color": color
        })
    # ─────────────────────────────────────────────────────────────────────────

    return {
        "summary": {
            "total_employees": total_employees,
            "present_today": present_today + late_today,
            "absent_today": absent_today,
            "tasks_assigned_today": tasks_assigned_today,
            "tasks_completed_today": tasks_completed_today,
            "pending_tasks": pending_tasks,
            "overall_on_time_rate": round(overall_on_time_rate, 1),
            "best_performer": best_performer["name"] if best_performer else "N/A"
        },
        "attendance_analytics": {
            "present": present_today,
            "late": late_today,
            "absent": absent_today,
            "pending_leaves": pending_leaves
        },
        "task_analytics": {
            "total_assigned": total_assigned,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "overdue_tasks": overdue_tasks,
            "due_today": tasks_due_today
        },
        "employees": employee_performance,
        "top_performers": {
            "by_tasks": top_by_tasks,
            "by_ontime": top_by_ontime,
            "by_attendance": top_by_attendance
        },
        "insights": {
            "needs_attention": needs_attention,
            "high_pending": high_pending,
            "most_consistent": top_by_attendance[0] if top_by_attendance else None
        },
        "charts": {
            "tasks_bar": {
                "labels": chart_tasks_names,
                "data": chart_tasks_data
            },
            "attendance_pie": {
                "labels": ["Present", "Late", "Absent"],
                "data": [present_today, late_today, absent_today]
            }
        },
        "trend": {
            "labels": trend_month_labels,
            "datasets": trend_datasets
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# ATTENDANCE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

class AttendanceUpdate(BaseModel):
    status: str
    time_in: Optional[str] = None
    time_out: Optional[str] = None

def _calc_hours(time_in: str, time_out: str) -> float:
    try:
        t_in  = datetime.datetime.strptime(time_in,  "%I:%M %p")
        t_out = datetime.datetime.strptime(time_out, "%I:%M %p")
        return round((t_out - t_in).total_seconds() / 3600.0, 1)
    except Exception:
        return 0.0

@router.get("/attendance")
async def get_all_attendance(
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    employee_id: str = "",
    date_from: str = "",
    date_to: str = "",
    status_filter: str = ""
):
    query = db.query(Attendance)
    if employee_id:
        query = query.filter(Attendance.user_id == int(employee_id))
    if date_from:
        query = query.filter(Attendance.date >= date_from)
    if date_to:
        query = query.filter(Attendance.date <= date_to)
    if status_filter:
        query = query.filter(Attendance.status == status_filter)

    records = query.order_by(Attendance.date.desc()).all()
    today = datetime.date.today()

    # Pre-fetch employees to avoid N+1
    emp_map = {u.id: u for u in db.query(User).filter(User.role == "Employee").all()}

    result = []
    for a in records:
        emp = emp_map.get(a.user_id)
        total_hours = _calc_hours(a.time_in, a.time_out) if a.time_in and a.time_out else 0.0
        missing_punchout = (a.date == today and bool(a.time_in) and not a.time_out)
        result.append({
            "id": a.id,
            "user_id": a.user_id,
            "employee_name": emp.employee_name if emp else "Unknown",
            "employee_code": emp.employee_code if emp else "-",
            "date": a.date.isoformat(),
            "time_in": a.time_in,
            "time_out": a.time_out,
            "total_hours": total_hours,
            "status": a.status,
            "missing_punchout": missing_punchout,
        })

    today_str = today.isoformat()
    today_recs = [r for r in result if r["date"] == today_str]
    summary = {
        "present_today":    len([r for r in today_recs if r["status"] == "Present"]),
        "absent_today":     len([r for r in today_recs if r["status"] == "Absent"]),
        "late_today":       len([r for r in today_recs if r["status"] == "Late"]),
        "missing_punchout": len([r for r in today_recs if r["missing_punchout"]]),
    }
    return {"records": result, "summary": summary}


@router.put("/attendance/{att_id}")
async def update_attendance(
    att_id: int,
    req: AttendanceUpdate,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    att = db.query(Attendance).filter(Attendance.id == att_id).first()
    if not att:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    att.status = req.status
    if req.time_in is not None:
        att.time_in  = req.time_in  or None
    if req.time_out is not None:
        att.time_out = req.time_out or None
    db.commit()
    return {"message": "Attendance updated"}


@router.get("/attendance/export")
async def export_attendance_csv(
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    employee_id: str = "",
    date_from: str = "",
    date_to: str = ""
):
    query = db.query(Attendance)
    if employee_id:
        query = query.filter(Attendance.user_id == int(employee_id))
    if date_from:
        query = query.filter(Attendance.date >= date_from)
    if date_to:
        query = query.filter(Attendance.date <= date_to)

    records = query.order_by(Attendance.date.desc()).all()
    emp_map = {u.id: u for u in db.query(User).filter(User.role == "Employee").all()}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Employee Name", "Employee Code", "Date", "Punch In", "Punch Out", "Total Hours", "Status"])
    for a in records:
        emp = emp_map.get(a.user_id)
        hours = _calc_hours(a.time_in, a.time_out) if a.time_in and a.time_out else 0
        writer.writerow([
            emp.employee_name if emp else "Unknown",
            emp.employee_code if emp else "-",
            a.date.isoformat(),
            a.time_in or "-",
            a.time_out or "-",
            hours,
            a.status
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_export.csv"}
    )


# ══════════════════════════════════════════════════════════════════════════════
# WORK FROM HOME REQUESTS (Admin)
# ══════════════════════════════════════════════════════════════════════════════

class WFHActionRequest(BaseModel):
    action: str  # "Approve" or "Reject"

@router.get("/wfh-requests")
async def get_wfh_requests(
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    status_filter: str = ""
):
    """Return all WFH requests, pending first then by date desc."""
    query = db.query(LeaveRequest).filter(LeaveRequest.leave_type == "Work From Home")
    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter)
    requests = query.order_by(LeaveRequest.status.asc(), LeaveRequest.start_date.desc()).all()
    emp_map = {u.id: u for u in db.query(User).filter(User.role == "Employee").all()}
    result = []
    for r in requests:
        emp = emp_map.get(r.user_id)
        result.append({
            "id": r.id,
            "employee_name": emp.employee_name if emp else "Unknown",
            "employee_code": emp.employee_code if emp else "-",
            "department": emp.department if emp else "-",
            "date": r.start_date.isoformat(),
            "reason": r.reason,
            "status": r.status,
        })
    pending_count = len([r for r in result if r["status"] == "Pending"])
    return {"requests": result, "pending_count": pending_count}

@router.put("/wfh-requests/{req_id}/action")
async def action_wfh_request(
    req_id: int,
    body: WFHActionRequest,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Approve or Reject a WFH request and create a notification."""
    if body.action not in ("Approve", "Reject"):
        raise HTTPException(status_code=400, detail="Action must be 'Approve' or 'Reject'.")
    wfh = db.query(LeaveRequest).filter(
        LeaveRequest.id == req_id,
        LeaveRequest.leave_type == "Work From Home"
    ).first()
    if not wfh:
        raise HTTPException(status_code=404, detail="WFH request not found.")
    if wfh.status != "Pending":
        raise HTTPException(status_code=400, detail=f"This request is already {wfh.status}.")

    new_status = "Approved" if body.action == "Approve" else "Rejected"
    wfh.status = new_status
    wfh.approved_by = user.id

    # Create notification
    emp = db.query(User).filter(User.id == wfh.user_id).first()
    emp_name = emp.employee_name if emp else "Employee"
    msg = (
        f"Your Work From Home request for {wfh.start_date.isoformat()} has been {new_status.lower()}."
    )
    priority = "Low" if new_status == "Approved" else "Medium"
    notif = Notification(
        type="wfh",
        message=msg,
        priority=priority,
        meta_data=_json.dumps({
            "ref_id": f"wfh_{wfh.id}_{new_status}",
            "title": f"WFH {new_status}",
            "employee_name": emp_name,
            "project_name": ""
        }),
        created_at=datetime.datetime.utcnow()
    )
    db.add(notif)
    db.commit()
    return {"message": f"WFH request {new_status.lower()} successfully."}


# ══════════════════════════════════════════════════════════════════════════════
# TASK MANAGEMENT

# ══════════════════════════════════════════════════════════════════════════════

class AdminTaskCreate(BaseModel):
    user_id: int
    client_name: str
    task_description: str
    deadline_date: datetime.date
    priority: str = "Medium"
    # Optional fields with defaults
    date: datetime.date = None
    project_name: str = ""
    start_date: datetime.date = None
    end_date: datetime.date = None
    editing_type: str = ""
    video_duration: float = 0.0
    status: str = "Not Started"
    harddisk_number: str = ""
    harddisk_directory: str = ""
    uploaded_to_drive: str = "No"
    drive_link: str = ""
    shoot_type: str = ""
    cameras_used: int = 1
    comments: str = ""

class AdminTaskUpdate(BaseModel):
    status: str
    priority: str
    deadline_date: Optional[datetime.date] = None
    drive_link: str = ""
    comments: str = ""

@router.get("/tasks")
async def get_all_tasks(
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    employee_id: str = "",
    status_filter: str = "",
    date_from: str = "",
    date_to: str = ""
):
    query = db.query(ProductivityRecord)
    if employee_id:
        query = query.filter(ProductivityRecord.user_id == int(employee_id))
    if status_filter:
        query = query.filter(ProductivityRecord.status == status_filter)
    if date_from:
        query = query.filter(ProductivityRecord.date >= date_from)
    if date_to:
        query = query.filter(ProductivityRecord.date <= date_to)

    records = query.order_by(ProductivityRecord.id.desc()).all()
    today = datetime.date.today()

    result = []
    for r in records:
        overdue = r.status != "Done" and r.deadline_date and r.deadline_date < today
        result.append({
            "id": r.id,
            "user_id": r.user_id,
            "employee_name": r.employee_name or "-",
            "client_name": r.client_name,
            "project_name": r.project_name,
            "date": r.date.isoformat() if r.date else None,
            "deadline_date": r.deadline_date.isoformat() if r.deadline_date else None,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "status": r.status,
            "priority": r.priority or "Medium",
            "editing_type": r.editing_type or "-",
            "shoot_type": r.shoot_type or "-",
            "video_duration": r.video_duration,
            "cameras_used": r.cameras_used,
            "expected_workload_hours": r.expected_workload_hours or 0,
            "drive_link": r.drive_link or "",
            "comments": r.comments or "",
            "overdue": bool(overdue),
        })

    completed = len([r for r in result if r["status"] == "Done"])
    overdue_count = len([r for r in result if r["overdue"]])
    return {
        "records": result,
        "summary": {
            "total": len(result),
            "completed": completed,
            "pending": len(result) - completed,
            "overdue": overdue_count,
        }
    }


@router.post("/tasks/assign")
async def assign_task(
    req: AdminTaskCreate,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    emp = db.query(User).filter(User.id == req.user_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    expected_hours = round(req.video_duration * req.cameras_used * 3, 1)
    new_record = ProductivityRecord(
        user_id=req.user_id,
        employee_name=emp.employee_name,
        designation=emp.designation,
        client_name=req.client_name,
        date=req.date or datetime.date.today(),
        project_name=req.project_name,
        start_date=req.start_date or datetime.date.today(),
        end_date=req.end_date or datetime.date.today(),
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
    return {"message": "Task assigned successfully"}


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: int,
    req: AdminTaskUpdate,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    record = db.query(ProductivityRecord).filter(ProductivityRecord.id == task_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    record.status = req.status
    record.priority = req.priority
    record.drive_link = req.drive_link
    record.comments = req.comments
    if req.deadline_date:
        record.deadline_date = req.deadline_date
    db.commit()
    return {"message": "Task updated"}


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    record = db.query(ProductivityRecord).filter(ProductivityRecord.id == task_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(record)
    db.commit()
    return {"message": "Task deleted"}


# ══════════════════════════════════════════════════════════════════════════════
# LEAVE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/leaves")
async def get_all_leaves(
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    employee_id: str = "",
    status_filter: str = ""
):
    query = db.query(LeaveRequest)
    if employee_id:
        query = query.filter(LeaveRequest.user_id == int(employee_id))
    if status_filter:
        query = query.filter(LeaveRequest.status == status_filter)

    leaves = query.order_by(LeaveRequest.start_date.desc()).all()
    emp_map = {u.id: u for u in db.query(User).filter(User.role == "Employee").all()}

    result = []
    for l in leaves:
        emp = emp_map.get(l.user_id)
        duration = (l.end_date - l.start_date).days + 1
        result.append({
            "id": l.id,
            "user_id": l.user_id,
            "employee_name": emp.employee_name if emp else "Unknown",
            "employee_code": emp.employee_code if emp else "-",
            "leave_type": l.leave_type,
            "start_date": l.start_date.isoformat(),
            "end_date": l.end_date.isoformat(),
            "duration_days": duration,
            "reason": l.reason,
            "status": l.status,
        })

    pending  = len([r for r in result if r["status"] == "Pending"])
    approved = len([r for r in result if r["status"] == "Approved"])
    rejected = len([r for r in result if r["status"] == "Rejected"])
    return {
        "leaves": result,
        "summary": {
            "total": len(result),
            "pending": pending,
            "approved": approved,
            "rejected": rejected
        }
    }


@router.put("/leaves/{leave_id}/approve")
async def approve_leave(
    leave_id: int,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    leave.status = "Approved"
    notif = Notification(
        type="leave",
        message=f"{leave.user_id}'s leave request from {leave.start_date.isoformat()} to {leave.end_date.isoformat()} was approved.",
        priority="Low",
        created_at=datetime.datetime.utcnow()
    )
    db.add(notif)
    db.commit()
    return {"message": "Leave approved"}


@router.put("/leaves/{leave_id}/reject")
async def reject_leave(
    leave_id: int,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    leave.status = "Rejected"
    notif = Notification(
        type="leave",
        message=f"{leave.user_id}'s leave request from {leave.start_date.isoformat()} to {leave.end_date.isoformat()} was rejected.",
        priority="Medium",
        created_at=datetime.datetime.utcnow()
    )
    db.add(notif)
    db.commit()
    return {"message": "Leave rejected"}


# ══════════════════════════════════════════════════════════════════════════════
# OFFICE LOCATION CONFIG
# ══════════════════════════════════════════════════════════════════════════════

class OfficeLocationUpdate(BaseModel):
    name: str = "Main Office"
    latitude: float
    longitude: float
    radius_meters: int = 100

@router.get("/office-location")
async def admin_get_office_location(
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    office = db.query(OfficeLocation).filter(OfficeLocation.is_active == True).first()
    if not office:
        return {"id": None, "name": "Not configured", "latitude": None, "longitude": None, "radius_meters": 100}
    return {
        "id": office.id,
        "name": office.name,
        "latitude": office.latitude,
        "longitude": office.longitude,
        "radius_meters": office.radius_meters,
    }

@router.put("/office-location")
async def admin_update_office_location(
    req: OfficeLocationUpdate,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    office = db.query(OfficeLocation).filter(OfficeLocation.is_active == True).first()
    if office:
        office.name = req.name
        office.latitude = req.latitude
        office.longitude = req.longitude
        office.radius_meters = req.radius_meters
    else:
        office = OfficeLocation(
            name=req.name,
            latitude=req.latitude,
            longitude=req.longitude,
            radius_meters=req.radius_meters,
            is_active=True
        )
        db.add(office)
    db.commit()
    return {"message": "Office location updated successfully"}


# ══════════════════════════════════════════════════════════════════════════════
# HOLIDAY MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

class HolidayCreate(BaseModel):
    name: str
    date: datetime.date
    day: Optional[str] = None
    description: Optional[str] = None
    holiday_type: str = "National"

class HolidayUpdate(BaseModel):
    name: str
    date: datetime.date
    day: Optional[str] = None
    description: Optional[str] = None
    holiday_type: str = "National"
    is_active: bool = True

@router.get("/holidays")
async def admin_get_holidays(
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    holiday_type: str = ""
):
    query = db.query(Holiday)
    if holiday_type:
        query = query.filter(Holiday.holiday_type == holiday_type)
    holidays = query.order_by(Holiday.date).all()
    result = []
    for h in holidays:
        result.append({
            "id": h.id,
            "name": h.name,
            "date": h.date.isoformat(),
            "day": h.date.strftime("%A"),
            "description": h.description or "",
            "holiday_type": h.holiday_type,
            "is_active": h.is_active,
        })
    return {"holidays": result, "total": len(result)}

@router.post("/holidays")
async def admin_create_holiday(
    req: HolidayCreate,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    import calendar
    day_name = req.day or req.date.strftime("%A")
    holiday = Holiday(
        name=req.name,
        date=req.date,
        day=day_name,
        description=req.description,
        holiday_type=req.holiday_type,
        is_active=True
    )
    db.add(holiday)
    db.commit()
    return {"message": "Holiday created successfully", "id": holiday.id}

@router.put("/holidays/{holiday_id}")
async def admin_update_holiday(
    holiday_id: int,
    req: HolidayUpdate,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    holiday.name = req.name
    holiday.date = req.date
    holiday.day = req.day or req.date.strftime("%A")
    holiday.description = req.description
    holiday.holiday_type = req.holiday_type
    holiday.is_active = req.is_active
    db.commit()
    return {"message": "Holiday updated"}

@router.delete("/holidays/{holiday_id}")
async def admin_delete_holiday(
    holiday_id: int,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    db.delete(holiday)
    db.commit()
    return {"message": "Holiday deleted"}


# ══════════════════════════════════════════════════════════════════════════════
# LEAVE BALANCE MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/leave-balances")
async def admin_get_leave_balances(
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    employees = db.query(User).filter(User.role == "Employee").all()
    result = []
    for emp in employees:
        balance = db.query(LeaveBalance).filter(LeaveBalance.user_id == emp.id).first()
        result.append({
            "user_id": emp.id,
            "employee_name": emp.employee_name,
            "employee_code": emp.employee_code or "-",
            "department": emp.department or "-",
            "total_leaves": balance.total_leaves if balance else 12,
            "used_leaves": balance.used_leaves if balance else 0,
            "remaining_leaves": balance.remaining_leaves if balance else 12,
            "year": balance.year if balance else datetime.date.today().year,
        })
    return {"balances": result}

class LeaveBalanceUpdate(BaseModel):
    total_leaves: int
    used_leaves: int

@router.put("/leave-balances/{user_id}")
async def admin_update_leave_balance(
    user_id: int,
    req: LeaveBalanceUpdate,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    balance = db.query(LeaveBalance).filter(LeaveBalance.user_id == user_id).first()
    if not balance:
        balance = LeaveBalance(
            user_id=user_id,
            year=datetime.date.today().year,
            total_leaves=req.total_leaves,
            used_leaves=req.used_leaves,
            remaining_leaves=req.total_leaves - req.used_leaves
        )
        db.add(balance)
    else:
        balance.total_leaves = req.total_leaves
        balance.used_leaves = req.used_leaves
        balance.remaining_leaves = req.total_leaves - req.used_leaves
    db.commit()
    return {"message": "Leave balance updated"}

# Also update leave balance when admin approves/rejects — patch existing approve/reject handlers
@router.put("/leaves/{leave_id}/approve-v2")
async def approve_leave_v2(
    leave_id: int,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Approve leave and deduct from leave balance."""
    leave = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if leave.status == "Approved":
        return {"message": "Already approved"}
    leave.status = "Approved"
    leave.approved_by = user.id
    # Deduct from balance if Annual leave
    if leave.leave_type == "Annual" and leave.days_count:
        balance = db.query(LeaveBalance).filter(LeaveBalance.user_id == leave.user_id).first()
        if balance:
            balance.used_leaves = min(balance.total_leaves, balance.used_leaves + leave.days_count)
            balance.remaining_leaves = max(0, balance.total_leaves - balance.used_leaves)
    db.commit()
    return {"message": "Leave approved and balance updated"}


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCTIVITY EDIT HISTORY (Admin View)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/productivity/edit-history")
async def admin_get_edit_history(
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    employee_id: str = "",
    record_id: str = ""
):
    query = db.query(ProductivityEditHistory)
    if employee_id:
        query = query.filter(ProductivityEditHistory.user_id == int(employee_id))
    if record_id:
        query = query.filter(ProductivityEditHistory.record_id == int(record_id))
    history = query.order_by(ProductivityEditHistory.edited_at.desc()).all()
    emp_map = {u.id: u for u in db.query(User).all()}
    result = []
    for h in history:
        emp = emp_map.get(h.user_id)
        rec = db.query(ProductivityRecord).filter(ProductivityRecord.id == h.record_id).first()
        result.append({
            "id": h.id,
            "record_id": h.record_id,
            "project_name": rec.project_name if rec else "—",
            "employee_name": emp.employee_name if emp else "Unknown",
            "employee_code": emp.employee_code if emp else "-",
            "edited_at": h.edited_at.isoformat() if h.edited_at else None,
            "old_values": json.loads(h.old_values) if h.old_values else {},
            "new_values": json.loads(h.new_values) if h.new_values else {},
        })
    return {"history": result, "total": len(result)}
