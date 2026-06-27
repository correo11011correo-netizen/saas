from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DB_URL = "postgresql://postgres:TFralZyHIJnjyZrNMtoDqqtUlPTsttvT@thomas.proxy.rlwy.net:24031/railway"
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
