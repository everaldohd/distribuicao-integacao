"""Tasks Celery para execução assíncrona do solver e notificações."""
import logging

from app.core.database import SessionLocal
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="run_solver", bind=True, max_retries=1)
def run_solver_task(self, schedule_id: str, manager_id: str):
    """Executa o CP-SAT solver em background para uma escala."""
    db = SessionLocal()
    try:
        from app.models.schedule import Schedule
        schedule = db.get(Schedule, schedule_id)
        if not schedule:
            logger.error(f"Schedule {schedule_id} não encontrado")
            return

        from app.services.optimizer.solver import ScheduleSolver
        solver = ScheduleSolver(db, schedule.calendar_id, manager_id)
        result = solver.solve(schedule_id)
        logger.info(f"Solver concluído para {schedule_id}: {result}")
        return result
    except Exception as exc:
        logger.exception(f"Erro no solver para {schedule_id}: {exc}")
        self.retry(exc=exc, countdown=10)
    finally:
        db.close()


@celery_app.task(name="post_publish_tasks")
def post_publish_tasks(schedule_id: str):
    """Após publicação: calcula saldo histórico e envia e-mails."""
    db = SessionLocal()
    try:
        # 1. Calcular saldo histórico
        from app.services.balance import compute_and_persist_monthly_balances
        compute_and_persist_monthly_balances(db, schedule_id)

        # 2. Notificar usuários escalados
        from app.models.schedule import Assignment, Schedule
        from app.models.user import User
        schedule = db.get(Schedule, schedule_id)
        if not schedule:
            return

        assigned_users = (
            db.query(User)
            .join(Assignment, Assignment.user_id == User.id)
            .filter(Assignment.schedule_id == schedule_id, Assignment.is_gap == False)
            .distinct()
            .all()
        )

        from app.services.notification import notify_schedule_published
        for user in assigned_users:
            try:
                notify_schedule_published(user.email, user.name, schedule.year, schedule.month)
            except Exception as e:
                logger.error(f"Falha ao notificar {user.email}: {e}")

    except Exception as exc:
        logger.exception(f"Erro em post_publish_tasks para {schedule_id}: {exc}")
    finally:
        db.close()


@celery_app.task(name="notify_exchange")
def notify_exchange(exchange_id: str, event: str):
    """Envia e-mail para eventos de troca: requested, accepted, rejected."""
    db = SessionLocal()
    try:
        from app.models.exchange import Exchange
        exchange = db.get(Exchange, exchange_id)
        if not exchange:
            return

        from app.models.user import User
        requester = db.get(User, exchange.requester_id)
        target = db.get(User, exchange.target_id) if exchange.target_id else None

        from app.services.notification import notify_exchange_requested, notify_exchange_resolved
        if event == "requested" and target:
            notify_exchange_requested(target.email, target.name, requester.name)
        elif event in ("accepted", "rejected") and requester:
            notify_exchange_resolved(requester.email, requester.name, accepted=(event == "accepted"))
    except Exception as exc:
        logger.exception(f"Erro em notify_exchange para {exchange_id}: {exc}")
    finally:
        db.close()
