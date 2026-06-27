import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
SECRET_KEY = os.getenv("SECRET_KEY", "my_super_secret_session_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Office GPS Location — Admin can update these in the DB (office_location table).
# These .env values serve as fallback defaults only.
OFFICE_LOCATION_NAME = os.getenv(
    "OFFICE_LOCATION_NAME",
    "C-Wing, G-3, Omkar Indrapuri, Kanyapada, Gokuldham, Goregaon (East), Mumbai - 40006"
)
OFFICE_LATITUDE = float(os.getenv("OFFICE_LATITUDE", "19.1737"))
OFFICE_LONGITUDE = float(os.getenv("OFFICE_LONGITUDE", "72.8702"))
OFFICE_RADIUS_METERS = int(os.getenv("OFFICE_RADIUS_METERS", "200"))
