from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, users, schedule_types, calendars, schedules, preferences, exchanges, balance, profiles, diagnostics
from app.core.config import settings
from app.core.logging import setup_logging, get_logger

setup_logging(settings.LOG_LEVEL)
logger = get_logger(__name__)

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


@app.get("/health")
def health():
    """Liveness probe simples (público): só confirma que a API está de pé."""
    return {"status": "ok"}
