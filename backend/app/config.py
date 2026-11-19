from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://examflow:examflow@localhost:5432/examflow"

    jwt_secret_key: str = "changeme"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_app_password: str = ""
    smtp_from_name: str = "Combine Mentor"

    ticket_storage_dir: str = "./storage/tickets"

    admin_default_username: str = "admin"
    admin_default_password: str = "changeme"


settings = Settings()
