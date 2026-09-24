"""Tabelas cm -> litros — tanque comboio 6000 L (PDF fabricante)."""
from __future__ import annotations

import json
import re
from pathlib import Path

from regua_tanque import litros_da_regua, litros_interpolado

COMBOIO_ALTURA_CHEIA_CM = 150.0
COMBOIO_CAPACIDADE_L = 6000.0

_DATA_JSON = Path(__file__).resolve().parent / "data" / "tabela_comboio_raw.json"


def _parse_tabela_pdf() -> list[tuple[float, float]]:
    """Extrai pontos (cm, litros) da tabela medidora do PDF do fabricante."""
    if not _DATA_JSON.is_file():
        return _tabela_fallback()

    raw = json.loads(_DATA_JSON.read_text(encoding="utf-8"))
    points: list[tuple[float, float]] = [(0.0, 0.0)]

    for row in raw[2:]:
        base_str = str(row[0] or "").strip()
        if not base_str.isdigit():
            continue
        base = int(base_str)
        if base > 200:
            continue
        txt = row[2] if (row[1] or "").strip().upper() == "LITROS" else row[1]
        if not txt:
            continue
        vals = [float(x) for x in re.findall(r"\d+", str(txt))]
        vals = [v for v in vals if v <= COMBOIO_CAPACIDADE_L + 500]
        if base == 0:
            for i, litros in enumerate(vals, start=1):
                points.append((float(i), litros))
        else:
            for i, litros in enumerate(vals):
                points.append((float(base + i), litros))

    points.sort(key=lambda x: x[0])
    # deduplica cm repetidos
    dedup: list[tuple[float, float]] = []
    for cm, litros in points:
        if dedup and dedup[-1][0] == cm:
            dedup[-1] = (cm, litros)
        else:
            dedup.append((cm, litros))
    return dedup


def _tabela_fallback() -> list[tuple[float, float]]:
    """Fallback se JSON do PDF não existir."""
    return [
        (0, 0), (77, 3280), (150, 6000),
    ]


TABELA_COMBOIO: list[tuple[float, float]] = _parse_tabela_pdf()


def litros_comboio(cm: float) -> float:
    if cm <= 0:
        return 0.0
    inter = litros_interpolado(cm, TABELA_COMBOIO)
    if inter is not None:
        return round(inter, 1)
    return litros_da_regua(cm, COMBOIO_ALTURA_CHEIA_CM, COMBOIO_CAPACIDADE_L, TABELA_COMBOIO)
