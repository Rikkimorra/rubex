import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

# Для SQLite нужно создать папку под файл БД и передать connect_args
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if db_path not in (":memory:",) and "/" in db_path:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
