import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Gestão de Escalas"
    SECRET_KEY: str = secrets.token_hex(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    LOG_LEVEL: str = "INFO"

    # CORS — lista separada por vírgula no .env
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Database
    DATABASE_URL: str = "postgresql://escalas:escalas@db:5432/escalas"

    # Redis / Celery
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/1"

    # E-mail
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@escalas.local"
    EMAIL_FROM_NAME: str = "Sistema de Escalas"

    # OR-Tools
    SOLVER_RANDOM_SEED: int = 42
    SOLVER_MAX_TIME_SECONDS: int = 60

    # Compensation defaults
    BALANCE_MONTH_NO_SCHEDULE: int = -10
    BALANCE_DESIRED_DATE_FULFILLED: int = -5
    BALANCE_COMMON_SCHEDULE: int = 0
    BALANCE_AVOIDED_DATE_ASSIGNED: int = 10

    # First manager seed
    FIRST_MANAGER_EMAIL: str = "admin@escalas.local"
    FIRST_MANAGER_PASSWORD: str = "change-me"
    FIRST_MANAGER_NAME: str = "Administrador"

    # Integração NEO (SSO): segredo compartilhado para validar o token de handoff.
    # Vazio = SSO desativado (usa apenas login local). Defina para habilitar.
    NEO_SSO_SECRET: str = ""
    NEO_SSO_TOKEN_TTL_SECONDS: int = 120  # tolerância de validade do token vindo do NEO
    # Cria automaticamente o perito na 1ª entrada via NEO se a matrícula não existir
    NEO_SSO_AUTO_PROVISION: bool = True

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
