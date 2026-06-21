import logging
import secrets

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Sentinela: chave não definida pelo ambiente. Não geramos uma chave aleatória
# silenciosa como default, porque ela muda a cada processo/réplica e derruba
# todas as sessões — ver tratamento em _ensure_secret_key().
_SECRET_NOT_SET = ""


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Gestão de Escalas"
    # Assina os tokens JWT. DEVE vir do ambiente (.env / secret manager).
    SECRET_KEY: str = _SECRET_NOT_SET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    LOG_LEVEL: str = "INFO"
    # Fuso para regras de data de negócio (antecedência de troca, expiração).
    # O container costuma rodar em UTC; sem isto, o "hoje" vira um dia perto da
    # meia-noite no Brasil (UTC−3). Mantém as comparações de data consistentes.
    TIMEZONE: str = "America/Sao_Paulo"

    # Sessão por cookie HttpOnly + CSRF (double-submit).
    # O JWT vai em cookie HttpOnly (inacessível a JS → protege contra XSS).
    # Um segundo cookie legível (csrf_token) é refletido no header X-CSRF-Token
    # pelo front e conferido pelo backend nas requisições que alteram estado.
    AUTH_COOKIE_NAME: str = "access_token"
    CSRF_COOKIE_NAME: str = "csrf_token"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    # Secure=True exige HTTPS no cookie. Em produção, defina COOKIE_SECURE=true.
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"  # lax cobre a maioria; "strict" é mais rígido

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


def _ensure_secret_key(s: Settings) -> None:
    """Garante uma SECRET_KEY utilizável e avisa quando ela não foi configurada.

    Em DEV, se nada vier do ambiente, geramos uma chave efêmera para não travar
    o boot — mas com aviso bem visível, pois ela invalida sessões a cada restart
    e difere entre réplicas. Em produção, configure SECRET_KEY no ambiente.
    """
    weak = {_SECRET_NOT_SET, "troque-por-uma-chave-segura-de-64-caracteres", "change-me"}
    if s.SECRET_KEY in weak:
        s.SECRET_KEY = secrets.token_hex(32)
        logger.warning(
            "SECRET_KEY não configurada — usando chave EFÊMERA (muda a cada "
            "restart e por réplica; sessões cairão). Defina SECRET_KEY no .env "
            "antes de produção."
        )


settings = Settings()
_ensure_secret_key(settings)
