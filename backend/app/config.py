from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ENVIRONMENT: str = "development"
    STORAGE_PATH: str = "/app/storage"
    API_BASE_URL: str = "http://localhost:8000"

    # Azure AD
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""
    AZURE_TENANT_ID: str = ""

    # Email
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@tickets.app"
    SMTP_TLS: bool = True

    # Frontend
    FRONTEND_URL: str = ""

    # Superadmin
    SUPERADMIN_API_KEY: str = ""

    # JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Celery
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

    def model_post_init(self, __context) -> None:
        if not self.CELERY_BROKER_URL:
            object.__setattr__(self, "CELERY_BROKER_URL", self.REDIS_URL)
        if not self.CELERY_RESULT_BACKEND:
            result_url = self.REDIS_URL.replace("/0", "/1") if self.REDIS_URL.endswith("/0") else self.REDIS_URL + "/1"
            object.__setattr__(self, "CELERY_RESULT_BACKEND", result_url)


settings = Settings()
