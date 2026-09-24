"""Tabelas cm -> litros — comboio (retangular 6000 L) e posto S-500."""
from __future__ import annotations

from regua_tanque import litros_da_regua

# Tanque comboio: retangular 6000 L, régua cheia ~150 cm
# Calibrado: 77 cm = 3.280 L (medição 24/09/2026)
COMBOIO_ALTURA_CHEIA_CM = 150.0
COMBOIO_CAPACIDADE_L = 6000.0
COMBOIO_CM_CALIBRADO = 77.0
COMBOIO_L_CALIBRADO = 3280.0


def _build_comboio_table() -> list[tuple[float, float]]:
    """Pontos da tabela medidora — passa por 0/0, 77/3280 e 150/6000."""
    pts: list[tuple[float, float]] = [(0.0, 0.0)]
    for cm in range(5, 151, 5):
        if cm <= COMBOIO_CM_CALIBRADO:
            litros = (cm / COMBOIO_CM_CALIBRADO) * COMBOIO_L_CALIBRADO
        else:
            litros = COMBOIO_L_CALIBRADO + (cm - COMBOIO_CM_CALIBRADO) * (
                (COMBOIO_CAPACIDADE_L - COMBOIO_L_CALIBRADO)
                / (COMBOIO_ALTURA_CHEIA_CM - COMBOIO_CM_CALIBRADO)
            )
        pts.append((float(cm), round(litros, 1)))
    pts.append((COMBOIO_CM_CALIBRADO, COMBOIO_L_CALIBRADO))
    pts.append((COMBOIO_ALTURA_CHEIA_CM, COMBOIO_CAPACIDADE_L))
    pts.sort(key=lambda x: x[0])
    # remove duplicatas de cm mantendo o ponto calibrado
    out: list[tuple[float, float]] = []
    for cm, litros in pts:
        if out and out[-1][0] == cm:
            if cm == COMBOIO_CM_CALIBRADO:
                out[-1] = (cm, COMBOIO_L_CALIBRADO)
        else:
            out.append((cm, litros))
    return out


TABELA_COMBOIO: list[tuple[float, float]] = _build_comboio_table()

# Posto S-500 — substituir pelos pontos da tabela física do posto quando disponível
POSTO_S500_ALTURA_CHEIA_CM = 200.0
POSTO_S500_CAPACIDADE_L = 30000.0
TABELA_POSTO_S500: list[tuple[float, float]] = [
    (0, 0),
    (50, 7500),
    (100, 15000),
    (150, 22500),
    (200, 30000),
]


def litros_comboio(cm: float) -> float:
    return litros_da_regua(
        cm, COMBOIO_ALTURA_CHEIA_CM, COMBOIO_CAPACIDADE_L, TABELA_COMBOIO
    )


def litros_posto_s500(cm: float) -> float:
    return litros_da_regua(
        cm, POSTO_S500_ALTURA_CHEIA_CM, POSTO_S500_CAPACIDADE_L, TABELA_POSTO_S500
    )
