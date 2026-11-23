from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://examflow:examflow@localhost:5432/examflow"
    # Total DB connections = pool_size + max_overflow; keep below the
    # database's connection limit.
    db_pool_size: int = 10
    db_max_overflow: int = 20

    jwt_secret_key: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720

    # Key used to encrypt sensitive student fields (Aadhaar) at rest. Must be a
    # Fernet key — generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # If left empty a key is derived from JWT_SECRET_KEY so local setups work
    # out of the box, but production should set its own: rotating the JWT
    # secret would otherwise make already-stored Aadhaar numbers unreadable.
    field_encryption_key: str = ""

    # --- OTP (mobile verification at signup, forgot password) ---
    # "console": test mode — no SMS is sent, the OTP is written to the server
    #            log (and returned to the browser if OTP_DEV_ECHO is true).
    # "msg91":   real SMS through MSG91's OTP API (needs DLT registration and
    #            an approved OTP template in the MSG91 dashboard).
    otp_provider: str = "console"
    otp_dev_echo: bool = False
    otp_expiry_minutes: int = 5
    otp_resend_seconds: int = 60
    otp_max_sends_per_hour: int = 5  # per mobile number and purpose
    otp_max_sends_per_ip_per_hour: int = 60
    otp_max_attempts: int = 5  # wrong guesses allowed per OTP
    msg91_auth_key: str = ""
    msg91_template_id: str = ""
    msg91_otp_url: str = "https://control.msg91.com/api/v5/otp"

    ticket_storage_dir: str = "./storage/tickets"

    admin_default_username: str = "admin"
    admin_default_password: str = "changeme"


settings = Settings()
