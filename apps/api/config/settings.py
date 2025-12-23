import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Simple settings object; extend as needed."""

    def __init__(self) -> None:
        self.env = os.getenv("APP_ENV", "local")
        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./rfp.db")
        self.storage_path = os.getenv("STORAGE_PATH", "storage")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        # SMTP / email settings
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        self.sender_email = os.getenv("SENDER_EMAIL", self.smtp_user or "no-reply@example.com")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

