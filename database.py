from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import urllib
from config import DATABASE_URL

# Optional: Ensure compatibility if parameters are missing from URL, though the env var provides the full URL
SQLALCHEMY_DATABASE_URL = DATABASE_URL

# Create SQLAlchemy engine
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
