import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
SECRET_KEY = os.getenv("SECRET_KEY", "my_super_secret_session_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Office GPS Location — Admin can update these in the DB (office_location table).
# These .env values serve as fallback defaults only.
OFFICE_LATITUDE = float(os.getenv("OFFICE_LATITUDE", "28.6139"))
OFFICE_LONGITUDE = float(os.getenv("OFFICE_LONGITUDE", "77.2090"))
OFFICE_RADIUS_METERS = int(os.getenv("OFFICE_RADIUS_METERS", "100"))
