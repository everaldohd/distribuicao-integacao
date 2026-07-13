"""Testes do parser de importação da planilha macro (app.services.xlsx_import).

Duas camadas:
  1. Testes PUROS da regra (coverage_from_grid) com grades sintéticas — sempre rodam.
  2. Testes de GABARITO contra a planilha real de exemplo. O gabarito foi conferido
     MANUALMENTE lendo as células cruas de cada mês (aplicando as regras à mão),
     de forma independente do parser. Se a planilha de exemplo não estiver presente
     (ela é grande e não versionada), esses testes são pulados.
"""
from pathlib import Path

import pytest

from app.services import xlsx_import as xi

FIXTURE = Path(__file__).parent / "fixtures" / "escala_dpi_sample.xlsx"
DEFAULT = xi.DEFAULT_DPI_SECTIONS


# ---------------------------------------------------------------------------
# 1) Regra pura — não depende da planilha
# ---------------------------------------------------------------------------

def test_regra_plantao_soma_secoes():
    grid = [{"day": 1, "weekend": False, "plantao": ["SPI", "SPD", "LBF"],
             "rm": "", "rt": "", "pim": "", "pit": ""}]
    cov = xi.coverage_from_grid(grid, ["SPI", "SPD"])
    assert cov[1]["Plantão 12h"] == 2  # SPI + SPD (LBF não selecionada)


def test_regra_fim_de_semana_funde_reserva_12h():
    grid = [{"day": 1, "weekend": True, "plantao": ["SPI"],
             "rm": "SOL", "rt": "SOL", "pim": "", "pit": ""}]
    cov = xi.coverage_from_grid(grid, ["SPI", "SOL"])
    assert cov[1]["Reserva 12h"] == 1
    assert cov[1]["Reserva Manhã"] == 0 and cov[1]["Reserva Tarde"] == 0


def test_regra_dia_util_nao_funde():
    grid = [{"day": 2, "weekend": False, "plantao": [],
             "rm": "SPD", "rt": "SPI", "pim": "SPI", "pit": "LBF"}]
    cov = xi.coverage_from_grid(grid, ["SPI", "SPD"])
    assert cov[2]["Reserva Manhã"] == 1 and cov[2]["Reserva Tarde"] == 1
    assert cov[2]["Reserva 12h"] == 0
    assert cov[2]["Pátio Manhã"] == 1 and cov[2]["Pátio Tarde"] == 0  # LBF não selecionada


def test_regra_fim_de_semana_secoes_diferentes_nao_funde():
    grid = [{"day": 3, "weekend": True, "plantao": [],
             "rm": "SPI", "rt": "SPD", "pim": "", "pit": ""}]
    cov = xi.coverage_from_grid(grid, ["SPI", "SPD"])
    assert cov[3]["Reserva 12h"] == 0
    assert cov[3]["Reserva Manhã"] == 1 and cov[3]["Reserva Tarde"] == 1


def test_regra_nada_selecionado_zera_tudo():
    grid = [{"day": 1, "weekend": False, "plantao": ["SPI"],
             "rm": "SPD", "rt": "SPD", "pim": "SPI", "pit": "SPI"}]
    cov = xi.coverage_from_grid(grid, [])
    assert all(v == 0 for v in cov[1].values())


# ---------------------------------------------------------------------------
# 2) Gabarito contra a planilha real (conferido à mão, célula a célula)
# ---------------------------------------------------------------------------

pytestmark_fixture = pytest.mark.skipif(
    not FIXTURE.exists(), reason="planilha de exemplo ausente em tests/fixtures/")

# (ano, mês) -> {dia: {tipo: quantidade esperada}}  (tipos omitidos = 0)
GABARITO = {
    (2025, 7): {
        1:  {"Plantão 12h": 1, "Reserva Tarde": 1},          # ter; B=SPI; RT=SPD
        5:  {"Plantão 12h": 1, "Reserva 12h": 1},            # sáb; B=SPI; RM=RT=SPBA
        6:  {"Plantão 12h": 2},                              # dom; A=SPD,B=SPBA; RM=RT=LBIOF(fora)
        12: {"Plantão 12h": 2, "Reserva 12h": 1},            # sáb; A=SIV,B=SPCEF; RM=RT=SPD
        24: {"Plantão 12h": 1, "Reserva Tarde": 1},          # qui; C=SOL; RT=SPI
    },
    (2025, 8): {
        2:  {"Reserva 12h": 1},                              # sáb; plantões fora; RM=RT=SPI
        6:  {"Plantão 12h": 2, "Reserva Manhã": 1, "Reserva Tarde": 1},  # qua; B=SPCEF,C=SPBA; RM=SPD,RT=SPI
        19: {"Plantão 12h": 1},                              # ter; B=SPI; RM=LBIOF,RT=SCPA(fora)
    },
    (2026, 7): {
        1:  {"Plantão 12h": 1, "Reserva Tarde": 1},          # qua; C=SPI; RT=SPD; pátios fora
        3:  {"Plantão 12h": 1, "Reserva Tarde": 1, "Pátio Tarde": 1},  # sex; C=SPI; RT=SPBA; PIT=SPI
        4:  {"Plantão 12h": 1, "Reserva 12h": 1},            # sáb; A=SPBA; RM=RT=SPD
        6:  {"Plantão 12h": 2, "Reserva Manhã": 1},          # seg; C=SPI,D=SPD; RM=SPBA,RT=LBF(fora)
    },
}


@pytest.mark.parametrize("ym", list(GABARITO), ids=lambda ym: f"{ym[0]}-{ym[1]:02d}")
@pytestmark_fixture
def test_gabarito_por_dia(ym):
    year, month = ym
    data = xi.parse_workbook(FIXTURE.read_bytes(), year, month)
    cov = xi.coverage_from_grid(data["grid"], DEFAULT)
    for day, expected in GABARITO[ym].items():
        got = cov[day]
        for tipo in xi.ALL_TYPES:
            esperado = expected.get(tipo, 0)
            assert got[tipo] == esperado, (
                f"{year}-{month:02d} dia {day} · {tipo}: esperado {esperado}, "
                f"obtido {got[tipo]} · dia completo = {got}")


@pytestmark_fixture
def test_secoes_detectadas():
    data = xi.parse_workbook(FIXTURE.read_bytes(), 2026, 7)
    secs = data["sections_found"]
    # seções do DPI presentes em jul/26
    for esperada in ["SPI", "SPBA", "SPD", "SOL", "SPCEF", "SPOIC", "SIV"]:
        assert esperada in secs
    # DISPENSADA não é seção
    assert "DISPENSADA" not in secs
    # pré-seleção = interseção com as do DPI
    assert set(data["default_selected"]) == set(xi.DEFAULT_DPI_SECTIONS) & set(secs)


@pytestmark_fixture
def test_reserva_12h_somente_em_fim_de_semana():
    data = xi.parse_workbook(FIXTURE.read_bytes(), 2026, 7)
    cov = xi.coverage_from_grid(data["grid"], DEFAULT)
    weekend_days = {c["day"] for c in data["grid"] if c["weekend"]}
    for day, tipos in cov.items():
        if tipos["Reserva 12h"] > 0:
            assert day in weekend_days, f"Reserva 12h em dia útil {day}"


@pytestmark_fixture
def test_meses_de_2025_sem_patio():
    # Nas abas de 2025 não há linhas PIM/PIT preenchidas → cobertura de Pátio = 0
    for ym in [(2025, 7), (2025, 8)]:
        data = xi.parse_workbook(FIXTURE.read_bytes(), *ym)
        cov = xi.coverage_from_grid(data["grid"], DEFAULT)
        total_patio = sum(t["Pátio Manhã"] + t["Pátio Tarde"] for t in cov.values())
        assert total_patio == 0, f"{ym} não deveria ter Pátio, obtido {total_patio}"
