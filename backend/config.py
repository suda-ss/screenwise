from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "sqlite:///./resume_screening.db"
    )
    upload_dir: str = os.getenv("UPLOAD_DIR", "./storage/uploads")
    cors_origins: tuple[str, ...] = tuple(
        item.strip()
        for item in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if item.strip()
    )
    dev_user_email: str = os.getenv("DEV_USER_EMAIL", "owner@example.com")
    session_cookie: str = os.getenv("AUTH_SESSION_COOKIE", "screenwise_session")
    session_days: int = int(os.getenv("AUTH_SESSION_DAYS", "30"))
    cookie_secure: bool = os.getenv("AUTH_COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}


settings = Settings()
