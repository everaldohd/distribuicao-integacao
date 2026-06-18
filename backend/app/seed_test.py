"""
Seed de teste: gera 100 peritos aleatórios para uso em desenvolvimento.

Usa o modelo ATUAL de perfis (por grupo) e preferências (por modalidade).
Pré-requisito: rode `python -m app.seed` antes (cria gestor, tipos e perfis do sistema).

Execute com: python -m app.seed_test
"""
import random
import uuid
from datetime import date, timedelta

from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User
from app.models.profile import Profile, ProfileGroupLimit
from app.models.eligibility import Eligibility
from app.models.schedule_type import ScheduleType
from app.models.preference import UserPreference, PreferenceType
from app.models.historical_balance import HistoricalBalance

SEED = 42
random.seed(SEED)

NOMES = [
    "Ana", "Bruno", "Carlos", "Daniela", "Eduardo", "Fernanda", "Gabriel",
    "Helena", "Igor", "Juliana", "Klaus", "Larissa", "Marcos", "Natália",
    "Otávio", "Paula", "Rafael", "Sabrina", "Thiago", "Ursula", "Vitor",
    "Wanderley", "Xavier", "Yara", "Zélia", "Adriano", "Beatriz", "Cláudio",
    "Débora", "Emerson", "Flávia", "Gustavo", "Heloísa", "Ivan", "Joana",
    "Leonardo", "Mariana", "Nícolas", "Olívia", "Pedro", "Quésia", "Ricardo",
    "Simone", "Tadeu", "Ubiratan", "Valéria", "Wellington", "Ximena", "Yago",
]
SOBRENOMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Costa",
    "Ferreira", "Rodrigues", "Almeida", "Nascimento", "Carvalho", "Freitas",
    "Gomes", "Martins", "Araújo", "Melo", "Barbosa", "Ribeiro", "Rocha",
    "Cardoso", "Mendes", "Castro", "Correia", "Dias", "Moreira", "Nunes",
    "Teixeira", "Azevedo", "Campos",
]

# Distribuição de perfis entre os 100 peritos (pesos relativos).
# Os perfis devem existir (criados por seed.py / migração).
PERFIL_PESOS = {
    "Lotado na Interna": 55,
    "Lotado na Interna com Restrição": 20,
    "Chefe": 10,
    "Lotado na Externa": 10,
    "Direção": 5,
}


def _dias_do_mes(ano: int, mes: int) -> list[date]:
    primeiro = date(ano, mes, 1)
    prox = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)
    ultimo = prox - timedelta(days=1)
    return [primeiro + timedelta(days=i) for i in range((ultimo - primeiro).days + 1)]


def seed_test():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.is_manager == True).first():
            print("ERRO: rode `python -m app.seed` antes do seed de teste.")
            return

        tipos = {t.name: t for t in db.query(ScheduleType).all()}
        if not tipos:
            print("ERRO: nenhum tipo de escala. Rode `python -m app.seed` primeiro.")
            return

        # Perfis disponíveis (precisam existir) e suas cotas por grupo
        perfis = {p.name: p for p in db.query(Profile).all()}
        faltando = [n for n in PERFIL_PESOS if n not in perfis]
        if faltando:
            print(f"ERRO: perfis ausentes {faltando}. Rode `python -m app.seed` para criá-los.")
            return
        group_limits = {p.id: {gl.group_name: gl.max_quantity for gl in p.group_limits} for p in perfis.values()}
        # Tipos elegíveis por grupo
        tipos_por_grupo: dict[str, list[ScheduleType]] = {}
        for t in tipos.values():
            tipos_por_grupo.setdefault(t.group_name or t.name, []).append(t)

        nomes_perfil = list(PERFIL_PESOS.keys())
        pesos = list(PERFIL_PESOS.values())

        hoje = date.today()
        dias_mes = _dias_do_mes(hoje.year, hoje.month)

        nomes_usados: set[str] = set()
        criados = 0
        for i in range(100):
            for _ in range(50):
                nome = f"{random.choice(NOMES)} {random.choice(SOBRENOMES)}"
                if nome not in nomes_usados:
                    nomes_usados.add(nome)
                    break
            email = f"perito.{i:03d}@peritos.teste"
            if db.query(User).filter(User.email == email).first():
                continue

            perfil = perfis[random.choices(nomes_perfil, weights=pesos, k=1)[0]]
            user = User(
                id=str(uuid.uuid4()), name=nome, email=email,
                hashed_password=hash_password("teste123"),
                is_manager=False, profile_id=perfil.id,
            )
            db.add(user)
            db.flush()

            # Elegibilidade: todos os tipos dos grupos com cota > 0 no perfil
            elegiveis: list[ScheduleType] = []
            for grupo, lim in group_limits[perfil.id].items():
                if lim > 0:
                    elegiveis.extend(tipos_por_grupo.get(grupo, []))
            for t in elegiveis:
                db.add(Eligibility(id=str(uuid.uuid4()), user_id=user.id, schedule_type_id=t.id, is_eligible=True))

            # Saldo inicial aleatório (somente para quem pode ser escalado)
            if elegiveis:
                saldo = float(random.randint(-20, 20))
                db.add(HistoricalBalance(
                    id=str(uuid.uuid4()), user_id=user.id, year=0, month=0,
                    delta=saldo, cumulative_balance=saldo,
                ))

            # Preferências por modalidade (2 a 5), restritas aos tipos elegíveis
            if elegiveis:
                for dia in random.sample(dias_mes, min(random.randint(2, 5), len(dias_mes))):
                    t = random.choice(elegiveis)
                    db.add(UserPreference(
                        id=str(uuid.uuid4()), user_id=user.id,
                        year=hoje.year, month=hoje.month, date=dia,
                        schedule_type_id=t.id,
                        type=random.choice([PreferenceType.DESIRED, PreferenceType.AVOID]),
                    ))

            criados += 1

        db.commit()
        print(f"Seed de teste concluído: {criados} peritos. Senha: teste123")
        print(f"Preferências geradas para {hoje.month:02d}/{hoje.year}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_test()
