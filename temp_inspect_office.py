from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL
from models import OfficeLocation

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)
session = Session()
office = session.query(OfficeLocation).filter(OfficeLocation.is_active == True).first()
print('office_row=', office)
if office:
    print('name=', office.name)
    print('lat=', office.latitude)
    print('lon=', office.longitude)
    print('radius=', office.radius_meters)
