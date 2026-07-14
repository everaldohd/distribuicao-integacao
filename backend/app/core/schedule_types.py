"""Nomes canônicos dos tipos de escala e sua definição-fonte.

Centraliza os literais que antes se repetiam em `seed`, `routers/calendars` e
`services/xlsx_import`. Mudou aqui → mudou em todo lugar.
Os nomes devem casar exatamente com `schedule_types.name` no banco.
"""

# Nomes dos tipos
PLANTAO_12H = "Plantão 12h"
RESERVA_MANHA = "Reserva Manhã"
RESERVA_TARDE = "Reserva Tarde"
RESERVA_12H = "Reserva 12h"
PATIO_MANHA = "Pátio Manhã"
PATIO_TARDE = "Pátio Tarde"

ALL_TYPE_NAMES = [
    PLANTAO_12H, RESERVA_MANHA, RESERVA_TARDE, RESERVA_12H, PATIO_MANHA, PATIO_TARDE,
]

# Grupos de cota
GRUPO_PLANTAO = "Plantão"
GRUPO_RESERVA = "Reserva"
GRUPO_PATIO = "Pátio"

# Definição-fonte dos tipos padrão (usada pelo seed inicial).
DEFAULT_SCHEDULE_TYPES = [
    {"name": PLANTAO_12H,   "requires_rest_day_after": True,  "display_order": 1, "group_name": GRUPO_PLANTAO, "group_weight": 1},
    {"name": RESERVA_MANHA, "requires_rest_day_after": False, "display_order": 2, "group_name": GRUPO_RESERVA, "group_weight": 1},
    {"name": RESERVA_TARDE, "requires_rest_day_after": False, "display_order": 3, "group_name": GRUPO_RESERVA, "group_weight": 1},
    {"name": RESERVA_12H,   "requires_rest_day_after": False, "display_order": 4, "group_name": GRUPO_RESERVA, "group_weight": 2},
    {"name": PATIO_MANHA,   "requires_rest_day_after": False, "display_order": 5, "group_name": GRUPO_PATIO,   "group_weight": 1},
    {"name": PATIO_TARDE,   "requires_rest_day_after": False, "display_order": 6, "group_name": GRUPO_PATIO,   "group_weight": 1},
]
