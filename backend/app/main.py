import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import SessionLocal
from app.models import ExamCenter, User
from app.routers import admin, auth, scan, student
from app.security import hash_password


def seed_defaults():
    db = SessionLocal()
    try:
        # The two default centers are seeded only on a brand-new installation
        # (no admin yet). Otherwise an admin who deleted them would see them
        # come back on the next restart.
        first_run = not db.query(User).filter(User.username == settings.admin_default_username).first()
        if first_run and db.query(ExamCenter).count() == 0:
            db.add_all(
                [
                    ExamCenter(
                        name="शि.प्र.मंडळीची नु. म. वि मुलींची प्रशाला व कनिष्ठ महाविद्यालय पुणे.",
                        code="CENTER_A",
                        district="Pune",
                    ),
                    ExamCenter(name="Biology Building, Sir Parashurambhau College, Pune", code="CENTER_B", district="Pune"),
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


logger = logging.getLogger("uvicorn.error")

_INSECURE_SECRETS = {"", "changeme", "secret", "change-me"}


def warn_about_insecure_settings():
    """Loud startup warnings for settings that are fine locally but unsafe in
    production. Logged only - nothing is blocked."""
    if settings.jwt_secret_key.strip().lower() in _INSECURE_SECRETS:
        logger.warning(
            "SECURITY: JWT_SECRET_KEY is not set (or is a placeholder). Anyone could forge admin/teacher/student "
            'logins. Set a long random value: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )
    if not settings.field_encryption_key:
        logger.warning(
            "SECURITY: FIELD_ENCRYPTION_KEY is not set; Aadhaar encryption key is derived from JWT_SECRET_KEY. "
            "Set a dedicated key before real students register (see .env.example)."
        )
    if settings.otp_provider == "firebase":
        if not (settings.firebase_project_id and settings.firebase_api_key):
            logger.warning("OTP: OTP_PROVIDER=firebase but FIREBASE_PROJECT_ID / FIREBASE_API_KEY are missing - OTP will not work.")
    elif settings.otp_provider == "startmessaging":
        if not settings.startmessaging_api_key:
            logger.warning("OTP: OTP_PROVIDER=startmessaging but STARTMESSAGING_API_KEY is missing - OTP sending will fail.")
    elif settings.otp_provider != "msg91":
        logger.warning(
            "OTP TEST MODE (OTP_PROVIDER=%s): no SMS is sent - OTPs only appear in this log%s. "
            "Set OTP_PROVIDER=startmessaging (STARTMESSAGING_API_KEY), msg91 or firebase before real students register.",
            settings.otp_provider,
            " and on screen (OTP_DEV_ECHO=true)" if settings.otp_dev_echo else "",
        )
    elif not settings.msg91_auth_key or not settings.msg91_template_id:
        logger.warning("OTP: OTP_PROVIDER=msg91 but MSG91_AUTH_KEY / MSG91_TEMPLATE_ID are missing - OTP sending will fail.")
    if settings.admin_default_password.strip().lower() in _INSECURE_SECRETS | {"admin", "password"}:
        logger.warning(
            "SECURITY: ADMIN_DEFAULT_PASSWORD is a default value. It only applies when the admin account is first "
            "created - make sure the live admin password is strong."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    warn_about_insecure_settings()
    seed_defaults()
    yield


app = FastAPI(title="Combine Mentor API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Lets the student portal read the admit card's download filename.
    expose_headers=["Content-Disposition"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(scan.router)
app.include_router(student.router)


@app.get("/health")
def health():
    return {"status": "ok"}
