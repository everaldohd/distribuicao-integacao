import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.ratelimit import limiter
from app.routers import (
    audit,
    auth,
    balance,
    calendars,
    diagnostics,
    exchanges,
    preferences,
    profiles,
    schedule_types,
    schedules,
    users,
)

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)
access_logger = get_logger("app.access")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Aplicação iniciada | CORS: %s", settings.CORS_ORIGINS)
    yield
    # Shutdown (nada a liberar por enquanto)


app = FastAPI(
    title="Sistema de Gestão de Escalas",
    version="1.0.0",
    description="API para gerenciamento, distribuição e auditoria de escalas de serviço.",
    lifespan=lifespan,
)

# Rate limit (anti força-bruta) — usado em /auth/login
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Cabeçalhos básicos de segurança em toda resposta (defesa em profundidade)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"     # impede MIME sniffing
    response.headers["X-Frame-Options"] = "DENY"               # impede clickjacking (iframe)
    response.headers["Referrer-Policy"] = "no-referrer"        # não vaza URL em links externos
    response.headers["X-XSS-Protection"] = "0"                 # desativa filtro legado (CSP é o caminho moderno)
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Loga toda requisição: método, rota, status e tempo. Erros 5xx saem como ERROR."""
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        access_logger.exception("%s %s -> 500 (%.0fms) [exceção não tratada]",
                                request.method, request.url.path, elapsed)
        raise
    elapsed = (time.perf_counter() - start) * 1000
    msg = "%s %s -> %d (%.0fms)"
    args = (request.method, request.url.path, response.status_code, elapsed)
    if response.status_code >= 500:
        access_logger.error(msg, *args)
    elif response.status_code >= 400:
        access_logger.warning(msg, *args)
    else:
        access_logger.info(msg, *args)
    return response


app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(schedule_types.router, prefix="/api/v1")
app.include_router(calendars.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(preferences.router, prefix="/api/v1")
app.include_router(exchanges.router, prefix="/api/v1")
app.include_router(balance.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(diagnostics.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")


@app.get("/health")
def health():
    """Liveness probe simples (público): só confirma que a API está de pé."""
    return {"status": "ok"}
