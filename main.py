from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from database import engine, Base, SessionLocal
from models import User
from auth import get_password_hash, get_current_user
from routers import auth as auth_router, employee as employee_router, admin as admin_router
from config import SECRET_KEY
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.role == "Admin").first()
        if not admin_user:
            new_admin = User(
                employee_name="System Admin",
                email="admin@blinkonce.local",
                username="admin",
                password_hash=get_password_hash("admin123"),
                designation="Administrator",
                role="Admin"
            )
            db.add(new_admin)
            db.commit()
    finally:
        db.close()
    
    yield

app = FastAPI(title="Blink Once Employees Productivity System", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, public, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("static/images", exist_ok=True)
os.makedirs("public", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API Routers under /api
app.include_router(auth_router.router, prefix="/api")
app.include_router(employee_router.router, prefix="/api/employee")
app.include_router(admin_router.router, prefix="/api/admin")

# Static Page Routes
@app.get("/")
async def root(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login")
    if user.role == "Admin":
        return RedirectResponse(url="/admin/dashboard")
    return RedirectResponse(url="/employee/dashboard")

@app.get("/login")
async def login_page():
    return FileResponse("public/login.html")

@app.get("/register")
async def register_page():
    return FileResponse("public/register.html")

@app.get("/employee/dashboard")
async def employee_dashboard_page():
    return FileResponse("public/employee_dashboard.html")

@app.get("/employee/profile")
async def employee_profile_page():
    return FileResponse("public/employee_profile.html")

@app.get("/admin/dashboard")
async def admin_dashboard_page():
    return FileResponse("public/admin_dashboard.html")

@app.get("/admin/settings")
async def admin_settings_page():
    return FileResponse("public/admin_settings.html")


@app.get("/admin/add-employee")
async def admin_add_employee_page():
    return FileResponse("public/admin_add_employee.html")

@app.get("/admin/view-employees")
async def admin_view_employees_page():
    return FileResponse("public/admin_view_employees.html")

@app.get("/admin/performance")
async def admin_performance_page():
    return FileResponse("public/admin_performance.html")

@app.get("/admin/attendance")
async def admin_attendance_page():
    return FileResponse("public/admin_attendance.html")

@app.get("/admin/tasks")
async def admin_tasks_page():
    return FileResponse("public/admin_tasks.html")

@app.get("/admin/leaves")
async def admin_leaves_page():
    return FileResponse("public/admin_leaves.html")
