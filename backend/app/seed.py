"""
Script de seed: cria o primeiro gestor, usuário de teste, tipos de escala e config de saldo.
Execute com: python -m app.seed
"""
from app.core.database import SessionLocal, engine
from app.core.database import Base
from app.core.security import hash_password
from app.core.config import settings
from app.models.user import User
from app.models.schedule_type import ScheduleType
from app.models.historical_balance import BalanceConfig
import uuid


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Gestor admin
        manager = db.query(User).filter(User.email == settings.FIRST_MANAGER_EMAIL).first()
        if not manager:
            manager = User(
                id=str(uuid.uuid4()),
                name=settings.FIRST_MANAGER_NAME,
                email=settings.FIRST_MANAGER_EMAIL,
                hashed_password=hash_password(settings.FIRST_MANAGER_PASSWORD),
                is_manager=True,
            )
            db.add(manager)
            print(f"Gestor criado: {settings.FIRST_MANAGER_EMAIL}")
        else:
            # Atualiza senha se mudou no .env
            manager.hashed_password = hash_password(settings.FIRST_MANAGER_PASSWORD)
            print(f"Gestor atualizado: {settings.FIRST_MANAGER_EMAIL}")

        # Usuário de teste
        test_user = db.query(User).filter(User.email == "usuario").first()
        if not test_user:
            db.add(User(
                id=str(uuid.uuid4()),
                name="Usuário Teste",
                email="usuario",
                hashed_password=hash_password("usuario"),
                is_manager=False,
            ))
            print("Usuário de teste criado: usuario / usuario")

        # Tipos de escala iniciais
        default_types = [
            {"name": "Plantão 12h",   "requires_rest_day_after": True,  "display_order": 1},
            {"name": "Reserva Manhã", "requires_rest_day_after": False, "display_order": 2},
            {"name": "Reserva Tarde", "requires_rest_day_after": False, "display_order": 3},
            {"name": "Reserva 12h",   "requires_rest_day_after": False, "display_order": 4},
            {"name": "Pátio Manhã",   "requires_rest_day_after": False, "display_order": 5},
            {"name": "Pátio Tarde",   "requires_rest_day_after": False, "display_order": 6},
        ]
        for t in default_types:
            if not db.query(ScheduleType).filter(ScheduleType.name == t["name"]).first():
                db.add(ScheduleType(id=str(uuid.uuid4()), **t))
                print(f"Tipo criado: {t['name']}")

        # Configuração de saldo padrão
        if not db.query(BalanceConfig).first():
            db.add(BalanceConfig(
                id=str(uuid.uuid4()),
                month_no_schedule=settings.BALANCE_MONTH_NO_SCHEDULE,
                desired_date_fulfilled=settings.BALANCE_DESIRED_DATE_FULFILLED,
                common_schedule=settings.BALANCE_COMMON_SCHEDULE,
                avoided_date_assigned=settings.BALANCE_AVOIDED_DATE_ASSIGNED,
            ))
            print("Configuração de saldo criada")

        db.commit()
        print("Seed concluído.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
