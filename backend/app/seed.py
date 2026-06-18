"""
Script de seed: cria o primeiro gestor, usuário de teste, tipos de escala e config de saldo.
Execute com: python -m app.seed
"""
import uuid

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.historical_balance import BalanceConfig
from app.models.schedule_type import ScheduleType
from app.models.user import User


def seed():
    # O schema é gerenciado pelo Alembic (alembic upgrade head no startup).
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

        # Tipos de escala iniciais (com grupo de cota e peso)
        default_types = [
            {"name": "Plantão 12h",   "requires_rest_day_after": True,  "display_order": 1, "group_name": "Plantão", "group_weight": 1},
            {"name": "Reserva Manhã", "requires_rest_day_after": False, "display_order": 2, "group_name": "Reserva", "group_weight": 1},
            {"name": "Reserva Tarde", "requires_rest_day_after": False, "display_order": 3, "group_name": "Reserva", "group_weight": 1},
            {"name": "Reserva 12h",   "requires_rest_day_after": False, "display_order": 4, "group_name": "Reserva", "group_weight": 2},
            {"name": "Pátio Manhã",   "requires_rest_day_after": False, "display_order": 5, "group_name": "Pátio",   "group_weight": 1},
            {"name": "Pátio Tarde",   "requires_rest_day_after": False, "display_order": 6, "group_name": "Pátio",   "group_weight": 1},
        ]
        for t in default_types:
            existing_type = db.query(ScheduleType).filter(ScheduleType.name == t["name"]).first()
            if not existing_type:
                db.add(ScheduleType(id=str(uuid.uuid4()), **t))
                print(f"Tipo criado: {t['name']}")
            elif existing_type.group_name is None:
                existing_type.group_name = t["group_name"]
                existing_type.group_weight = t["group_weight"]

        # Perfis do sistema (cria apenas se ausente — não sobrescreve limites já ajustados)
        from app.models.profile import Profile, ProfileGroupLimit
        system_profiles = [
            ("Lotado na Interna",               {"Plantão": 1, "Reserva": 2, "Pátio": 0}, False, False),
            ("Lotado na Interna com Restrição", {"Plantão": 0, "Reserva": 0, "Pátio": 1}, False, False),
            ("Lotado na Externa",               {"Plantão": 0, "Reserva": 0, "Pátio": 0}, False, False),
            ("Chefe",                           {"Plantão": 1, "Reserva": 2, "Pátio": 0}, False, False),
            ("Direção",                         {"Plantão": 0, "Reserva": 0, "Pátio": 0}, False, False),
            ("Fora do Integração",              {"Plantão": 0, "Reserva": 0, "Pátio": 0}, True,  False),
            ("Personalizado",                   None,                                     False, True),
        ]
        for nome, limites, is_default, is_custom in system_profiles:
            if not db.query(Profile).filter(Profile.name == nome).first():
                p = Profile(id=str(uuid.uuid4()), name=nome, is_default=is_default, is_custom=is_custom, is_system=True)
                db.add(p)
                db.flush()
                if limites:
                    for grupo, lim in limites.items():
                        db.add(ProfileGroupLimit(id=str(uuid.uuid4()), profile_id=p.id, group_name=grupo, max_quantity=lim))
                print(f"Perfil criado: {nome}")

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
