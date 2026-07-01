from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
from models import User
from auth import get_password_hash, verify_password, get_current_user

router = APIRouter()

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str
    rewrite_password: str

class LoginRequest(BaseModel):
    username: str
    password: str

@router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"id": user.id, "username": user.username, "employee_name": user.employee_name, "role": user.role}

@router.get("/check-email")
async def check_email(email: str, db: Session = Depends(get_db)):
    """Check if email is registered by admin (exists in users table)."""
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Email is not registered by the Admin")

    return {"valid": True, "message": "Email is registered by Admin"}

@router.post("/register")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if req.password != req.rewrite_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    # Check if email exists in the database (must be pre-registered by admin)
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email is not registered by the Admin. Please contact your admin.")
    
    # Check if email already has password set (already registered)
    if user.password_hash and user.password_hash.strip() != "":
        raise HTTPException(status_code=404, detail="Email is not registered by the Admin")
    
    # Check if username already exists on another account
    existing_username = db.query(User).filter(User.username == req.username).first()
    if existing_username and existing_username.id != user.id:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Update the user with registration details and set password
    user.username = req.username
    user.password_hash = get_password_hash(req.password)
    db.commit()
    return {"message": "Registration successful"}

@router.post("/login")
async def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        # Fallback: try matching by email address
        user = db.query(User).filter(User.email == req.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Check if user has set a password (completed registration)
    if not user.password_hash:
        raise HTTPException(status_code=401, detail="Account not yet registered. Please complete your registration first.")
    
    if not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    request.session["user_id"] = user.id
    return {"message": "Login successful", "role": user.role}

@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logout successful"}

@router.get("/logout")
async def logout_get(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
