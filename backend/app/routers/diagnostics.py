"""
Endpoint de diagnóstico (gestor): verifica a saúde dos componentes do sistema e
aponta exatamente o que está OK e o que falhou.

Checagens:
  - database : conexão com o PostgreSQL
  - redis    : fila/broker do Celery
  - celery   : há worker(s) respondendo (necessário para gerar escalas)
  - seed     : dados base existem (gestor, tipos de escala, perfis, config de saldo)

Status geral:
  - "ok"       : tudo funcionando
  - "degraded" : algo não-crítico falhou (ex.: nenhum worker Celery — a app abre, mas
                 a geração de escala não roda até subir o worker)
  - "error"    : algo crítico falhou (banco indisponível ou seed ausente)
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.historical_balance import BalanceConfig
from app.models.operational_calendar import OperationalCalendar
from app.models.profile import Profile
from app.models.schedule import Schedule
from app.models.schedule_type import ScheduleType
from app.models.user import User
from app.routers.deps import get_current_manager

logger = get_logger(__name__)
router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


def _check_database(db: Session) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"ok": True, "detail": "PostgreSQL respondeu."}
    except Exception as e:
        return {"ok": False, "detail": f"Falha no banco de dados: {e}"}


def _check_redis() -> dict:
    try:
        import redis
        client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        client.ping()
        return {"ok": True, "detail": "Redis respondeu ao PING."}
    except Exception as e:
        return {"ok": False, "detail": f"Falha no Redis: {e}"}


def _check_celery() -> dict:
    try:
        from app.workers.celery_app import celery_app
        replies = celery_app.control.ping(timeout=2) or []
        if not replies:
            return {"ok": False, "detail": "Nenhum worker Celery respondeu (escalas não serão geradas)."}
        return {"ok": True, "detail": f"{len(replies)} worker(s) Celery ativo(s)."}
    except Exception as e:
        return {"ok": False, "detail": f"Falha ao consultar o Celery: {e}"}


def _check_seed(db: Session) -> dict:
    try:
        gestores = db.query(User).filter(User.is_manager == True).count()
        tipos = db.query(ScheduleType).count()
        perfis = db.query(Profile).count()
        tem_config = db.query(BalanceConfig).first() is not None

        problemas = []
        if gestores == 0:
            problemas.append("nenhum gestor cadastrado")
        if tipos == 0:
            problemas.append("nenhum tipo de escala")
        if perfis == 0:
            problemas.append("nenhum perfil")
        if not tem_config:
            problemas.append("sem configuração de saldo")

        detail = f"gestores={gestores}, tipos={tipos}, perfis={perfis}, config_saldo={'sim' if tem_config else 'não'}"
        if problemas:
            detail += " | PENDÊNCIAS: " + ", ".join(problemas) + " (rode `python -m app.seed`)"
        return {"ok": not problemas, "detail": detail}
    except Exception as e:
        return {"ok": False, "detail": f"Falha ao verificar o seed: {e}"}


@router.get("/", dependencies=[Depends(get_current_manager)])
def run_diagnostics(db: Session = Depends(get_db)):
    checks = {
        "database": _check_database(db),
        "redis": _check_redis(),
        "celery": _check_celery(),
        "seed": _check_seed(db),
    }

    # Resumo rápido de volumetria (não falha o diagnóstico se der erro)
    try:
        summary = {
            "usuarios": db.query(User).count(),
            "calendarios": db.query(OperationalCalendar).count(),
            "escalas": db.query(Schedule).count(),
        }
    except Exception:
        summary = {}

    # database e seed são críticos; redis e celery apenas degradam
    critico_ok = checks["database"]["ok"] and checks["seed"]["ok"]
    tudo_ok = all(c["ok"] for c in checks.values())
    status = "ok" if tudo_ok else ("error" if not critico_ok else "degraded")

    if status != "ok":
        falhas = [nome for nome, c in checks.items() if not c["ok"]]
        logger.warning("Diagnóstico %s | falhas: %s", status, ", ".join(falhas))

    return {
        "status": status,
        "checks": checks,
        "summary": summary,
        "integracoes": {"sso_neo_habilitado": bool(settings.NEO_SSO_SECRET)},
    }
