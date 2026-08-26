from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal
from app.models import ExamCenter, User
from app.routers import admin, auth, scan
from app.security import hash_password


def seed_defaults():
    db = SessionLocal()
    try:
        if db.query(ExamCenter).count() == 0:
            db.add_all(
                [
                    ExamCenter(
                        name="शि.प्र.मंडळीची नु. म. वि मुलींची प्रशाला व कनिष्ठ महाविद्यालय पुणे.",
                        code="CENTER_A",
                    ),
                    ExamCenter(name="Biology Building, Sir Parashurambhau College, Pune", code="CENTER_B"),
                ]
            )
            db.commit()

        if not db.query(User).filter(User.username == settings.admin_default_username).first():
            db.add(
                User(
                    username=settings.admin_default_username,
                    password_hash=hash_password(settings.admin_default_password),
                    full_name="Administrator",
                    role="admin",
                    is_active=True,
                )
            )
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_defaults()
    yield


app = FastAPI(title="Examflow API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(scan.router)


@app.get("/health")
def health():
    return {"status": "ok"}
