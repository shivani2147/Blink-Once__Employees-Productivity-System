from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from models import User, ProductivityRecord
from auth import get_current_admin, get_password_hash
from fastapi import UploadFile, File, Form
import shutil
import os

router = APIRouter()

class AdminSettingsUpdate(BaseModel):
    username: str
    password: Optional[str] = None

@router.get("/data")
async def get_admin_dashboard_data(
    user: User = Depends(get_current_admin), 
    db: Session = Depends(get_db),
    employee_filter: str = "",
    client_filter: str = "",
    project_filter: str = "",
    status_filter: str = ""
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

@router.put("/settings")
async def update_admin_settings(
    req: AdminSettingsUpdate,
    request: Request,
    user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    user.username = req.username
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
    emergency_contact: str = Form(...),
    highest_qualification: Optional[str] = Form(None),
    institution_name: Optional[str] = Form(None),
    date_of_joining: str = Form(...),
    department: List[str] = Form(...),
    designation: List[str] = Form(...),
    salary_type: str = Form(...),
    salary_value: str = Form(...),
    experience: Optional[str] = Form(None),
    skills: Optional[str] = Form(None),
    software_knowledge: Optional[str] = Form(None),
    camera_skill_level: Optional[str] = Form(None),
    editing_type: Optional[str] = Form(None),
    photo: UploadFile = File(...),
    resume: UploadFile = File(...),
    aadhaar_front: UploadFile = File(...),
    aadhaar_back: UploadFile = File(...),
    certificates: UploadFile = File(...),
):
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
        if not file:
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
        salary_value=salary_value,
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
