"""Reset controlado dos dados de teste.

MANTÉM: apenas o cadastro — usuários (com senhas), perfis/cotas, elegibilidades,
        tipos de escala, configuração de pesos do saldo, logs de auditoria.
APAGA:  toda a pontuação (saldos históricos), preferências, indisponibilidades
        (férias/licenças), todos os calendários e tudo que depende deles
        (escalas, atribuições, trocas, auditorias do solver).

Uso (dentro do container backend):
    python -m app.reset_test_data           # mostra o que será apagado e pede confirmação
    python -m app.reset_test_data --yes     # executa sem perguntar (para scripts)
"""

import sys

from sqlalchemy import delete, func, select

from app.core.database import SessionLocal
from app.models.audit import SolverAudit
from app.models.exchange import Exchange
from app.models.historical_balance import HistoricalBalance
from app.models.operational_calendar import CalendarDay, DayCoverage, OperationalCalendar
from app.models.preference import UserPreference
from app.models.schedule import Assignment, Schedule
from app.models.unavailability import Unavailability

# Ordem importa: filhos antes dos pais (respeita as FKs sem depender de CASCADE)
_TARGETS = [
    ("Trocas", Exchange),
    ("Auditorias do solver", SolverAudit),
    ("Atribuições", Assignment),
    ("Escalas", Schedule),
    ("Coberturas de dia", DayCoverage),
    ("Dias de calendário", CalendarDay),
    ("Calendários", OperationalCalendar),
    ("Saldos históricos (pontuação)", HistoricalBalance),
    ("Preferências", UserPreference),
    ("Indisponibilidades (férias/licenças)", Unavailability),
]


def main() -> None:
    assume_yes = "--yes" in sys.argv

    with SessionLocal() as db:
        counts = [(label, db.scalar(select(func.count()).select_from(model)) or 0) for label, model in _TARGETS]

        print("Este reset vai APAGAR:")
        for label, count in counts:
            print(f"  - {label}: {count} registro(s)")
        print("Usuários (com perfis/elegibilidades) e tipos de escala serão MANTIDOS.")

        total = sum(c for _, c in counts)
        if total == 0:
            print("Nada a apagar — banco já está limpo.")
            return

        if not assume_yes:
            answer = input("Confirma? Digite 'sim' para prosseguir: ").strip().lower()
            if answer != "sim":
                print("Cancelado — nada foi apagado.")
                return

        # Tudo numa transação: ou apaga tudo, ou nada (sem estado pela metade)
        for label, model in _TARGETS:
            db.execute(delete(model))
        db.commit()
        print(f"Concluído: {total} registro(s) apagado(s).")


if __name__ == "__main__":
    main()
