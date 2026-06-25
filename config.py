import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
SECRET_KEY = os.getenv("SECRET_KEY", "my_super_secret_session_key") # In production, use environment variables
ALGORITHM = os.getenv("ALGORITHM", "HS256")
