import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, users, schedule_types, calendars, schedules, preferences, exchanges, balance, profiles, diagnostics, audit
from app.core.config import settings
from app.core.logging import setup_logging, get_logger

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)
access_logger = get_logger("app.access")

app = FastAPI(
    title="Sistema de Gestão de Escalas",
    version="1.0.0",
    description="API para gerenciamento, distribuição e auditoria de escalas de serviço.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.on_event("startup")
async def on_startup():
    logger.info("Aplicação iniciada | CORS: %s", settings.CORS_ORIGINS)

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
