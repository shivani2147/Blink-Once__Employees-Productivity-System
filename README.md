# Blink Once Employees Productivity System

A role-based, complete production-style web application for employee productivity tracking.

## Tech Stack
- Backend: FastAPI
- Frontend: HTML, CSS (Vanilla)
- Database: Microsoft SQL Server (via pyodbc & SQLAlchemy)
- Authentication: bcrypt, session-based auth

## Setup Instructions

1. **Install uv (or use your preferred virtual environment)**:
   ```cmd
   uv venv
   .venv\Scripts\activate
   uv pip install -r requirements.txt
   ```

2. **Configure Database**:
   - Ensure you have Microsoft SQL Server installed and running.
   - Verify the `SERVER` and `DATABASE` values in `config.py`. 
   - Note: The database and tables will be created automatically via SQLAlchemy, provided the server exists and the credentials allow creation (if DB does not exist, you might need to create the `BlinkOnce_EmployeesProductivity` database manually in SQL Server first).

3. **Run Application**:
   ```cmd
   uvicorn main:app --reload
   ```

4. **Default Admin User**:
   - Upon first startup, the default admin is created automatically:
   - **Username**: admin
   - **Password**: admin123

## Explanation

1. **Est. Workload** : 
- The "Est. Workload" (Estimated Workload in hours) is calculated automatically when an employee submits a new productivity record, and it's based entirely on the number of cameras used for the project.

Here is the exact formula used in your backend (routers/employee.py):

Base Hours: It starts with a base assumption of 10.0 hours for a standard 1-camera project.
Multiplier: For every additional camera used beyond the first one, a 0.5 (or 50%) multiplier is added.
Calculation: Workload = Base Hours × (1.0 + (Cameras Used - 1) × 0.5)
Examples:

1 Camera: 10.0 × 1.0 = 10.0 hours
2 Cameras: 10.0 × 1.5 = 15.0 hours
3 Cameras: 10.0 × 2.0 = 20.0 hours
4 Cameras: 10.0 × 2.5 = 25.0 hours
This means every extra camera adds an estimated 5 hours of editing workload.


2. **Est. Completion Time** : 
- The "Number of Days" displayed in the admin dashboard is calculated using both the estimated editing workload and the actual video duration. The system uses whichever is larger as the basis for completion time (so long video files will push the completion time accordingly).
- The formula is: Number of Days = max(Est. Workload Hours, Video Duration Hours) / 8
Examples:

- Workload = 10 hrs, Video Duration = 2 hrs → max(10,2) = 10 → 10 ÷ 8 = 1.25 days
- Workload = 15 hrs, Video Duration = 20 hrs → max(15,20) = 20 → 20 ÷ 8 = 2.5 days

3. **Video Duration**: 
- "Video Duration" is the total length of the final edited video, measured in hours. 
- Unlike the estimated workload, this is a manual input field that the employee fills in when submitting the productivity record. It represents the actual time duration of the video file they delivered for the project. 
