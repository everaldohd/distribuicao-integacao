"""
Migração: novo modelo de perfis por GRUPO (Plantão / Reserva / Pátio).
- Adiciona colunas group_name/group_weight em schedule_types e flags em profiles.
- Cria tabelas profile_group_limits e user_group_limits.
- Classifica os tipos de escala em grupos (Reserva 12h pesa 2).
- Substitui os perfis antigos pelos novos perfis fixos + Fora do Integração + Personalizado.
- Reatribui peritos de teste ao perfil 'Lotado na Interna'.

Execute uma vez: python -m app.migrate_profiles
"""
from sqlalchemy import text
from app.core.database import SessionLocal, engine, Base
from app.models.schedule_type import ScheduleType
from app.models.profile import Profile, ProfileGroupLimit, UserGroupLimit, ProfileRule
from app.models.user import User
import uuid

GROUPS = ["Plantão", "Reserva", "Pátio"]

# tipo -> (grupo, peso)
TIPO_GRUPO = {
    "Plantão 12h":   ("Plantão", 1),
    "Reserva Manhã": ("Reserva", 1),
    "Reserva Tarde": ("Reserva", 1),
    "Reserva 12h":   ("Reserva", 2),
    "Pátio Manhã":   ("Pátio", 1),
    "Pátio Tarde":   ("Pátio", 1),
}

# perfil -> {grupo: limite}, flags
PERFIS = [
    ("Lotado na Interna",                {"Plantão": 1, "Reserva": 2, "Pátio": 0}, False, False, True),
    ("Lotado na Interna com Restrição",  {"Plantão": 0, "Reserva": 0, "Pátio": 1}, False, False, True),
    ("Lotado na Externa",                {"Plantão": 0, "Reserva": 0, "Pátio": 0}, False, False, True),
    ("Chefe",                            {"Plantão": 1, "Reserva": 2, "Pátio": 0}, False, False, True),
    ("Direção",                          {"Plantão": 0, "Reserva": 0, "Pátio": 0}, False, False, True),
    ("Fora do Integração",               {"Plantão": 0, "Reserva": 0, "Pátio": 0}, True,  False, True),  # is_default
    ("Personalizado",                    None,                                     False, True,  True),  # is_custom
]


def run():
    # 1. Colunas novas (idempotente)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE schedule_types ADD COLUMN IF NOT EXISTS group_name VARCHAR(50)"))
        conn.execute(text("ALTER TABLE schedule_types ADD COLUMN IF NOT EXISTS group_weight INTEGER NOT NULL DEFAULT 1"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_default BOOLEAN NOT NULL DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_custom BOOLEAN NOT NULL DEFAULT FALSE"))
        conn.execute(text("ALTER TABLE profiles ADD COLUMN IF NOT EXISTS is_system BOOLEAN NOT NULL DEFAULT FALSE"))

    # 2. Tabelas novas
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 3. Classifica tipos em grupos
        for t in db.query(ScheduleType).all():
            if t.name in TIPO_GRUPO:
                t.group_name, t.group_weight = TIPO_GRUPO[t.name]
        db.flush()

        # 4. Remove perfis antigos (e suas regras/limites por cascade) e reatribui peritos
        nomes_novos = {p[0] for p in PERFIS}
        antigos = db.query(Profile).filter(~Profile.name.in_(nomes_novos)).all()
        # Limpa ProfileRule órfãos do modelo antigo
        for p in antigos:
            db.query(ProfileRule).filter(ProfileRule.profile_id == p.id).delete()
            db.query(ProfileGroupLimit).filter(ProfileGroupLimit.profile_id == p.id).delete()
            db.delete(p)
        db.flush()

        # 5. Cria/atualiza perfis novos
        perfil_por_nome = {}
        for nome, limites, is_default, is_custom, is_system in PERFIS:
            perfil = db.query(Profile).filter(Profile.name == nome).first()
            if not perfil:
                perfil = Profile(id=str(uuid.uuid4()), name=nome)
                db.add(perfil)
            perfil.is_default = is_default
            perfil.is_custom = is_custom
            perfil.is_system = is_system
            db.flush()
            perfil_por_nome[nome] = perfil
            # Limpa e recria limites por grupo (exceto Personalizado, que é por perito)
            db.query(ProfileGroupLimit).filter(ProfileGroupLimit.profile_id == perfil.id).delete()
            if limites is not None:
                for grupo, lim in limites.items():
                    db.add(ProfileGroupLimit(
                        id=str(uuid.uuid4()), profile_id=perfil.id, group_name=grupo, max_quantity=lim
                    ))
        db.flush()

        # 6. Reatribui todos os peritos (não-gestores) a 'Lotado na Interna'
        interna = perfil_por_nome["Lotado na Interna"]
        peritos = db.query(User).filter(User.is_manager == False).all()
        for u in peritos:
            u.profile_id = interna.id
        # Gestores ficam sem perfil (caem no padrão Fora do Integração = 0)
        for g in db.query(User).filter(User.is_manager == True).all():
            g.profile_id = None

        db.commit()
        print(f"Migração concluída.")
        print(f"  Tipos classificados em grupos: {len(TIPO_GRUPO)}")
        print(f"  Perfis: {', '.join(perfil_por_nome.keys())}")
        print(f"  Peritos reatribuídos a 'Lotado na Interna': {len(peritos)}")
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
