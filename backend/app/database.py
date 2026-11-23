from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# Sized for peak load (thousands of students logging in / downloading around
# the same time): FastAPI runs up to 40 sync requests concurrently, and with
# SQLAlchemy's default of 5 (+10 overflow) connections the rest would queue
# and eventually fail with "QueuePool limit reached". pool_recycle replaces
# connections before hosted Postgres (e.g. Neon) drops idle ones.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=30,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
