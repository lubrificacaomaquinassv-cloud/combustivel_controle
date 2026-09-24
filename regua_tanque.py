"""Conversão régua (cm) → litros — tanque cilíndrico horizontal.

Perto do ideal para comboio: o volume não é linear com a altura
(cheio no meio, pouco nos extremos). Ajuste fino: cadastre pontos
da tabela gravada na régua, se existir.
"""
from __future__ import annotations

import math


def litros_cilindro(cm: float, altura_cheia_cm: float, capacidade_l: float) -> float:
    """Volume de cilindro horizontal pela altura molhada da régua."""
    if altura_cheia_cm <= 0 or capacidade_l <= 0 or cm <= 0:
        return 0.0
    if cm >= altura_cheia_cm:
        return float(capacidade_l)
    r = altura_cheia_cm / 2.0
    h = float(cm)
    ratio = max(-1.0, min(1.0, (r - h) / r))
    area = r * r * math.acos(ratio) - (r - h) * math.sqrt(max(0.0, 2 * r * h - h * h))
    return capacidade_l * area / (math.pi * r * r)


def litros_interpolado(cm: float, pontos: list[tuple[float, float]]) -> float | None:
    """Interpolação linear entre pontos (cm, litros) da tabela da régua."""
    pts = sorted((float(c), float(l)) for c, l in pontos if c is not None)
    if len(pts) < 2:
        return None
    x = float(cm)
    if x <= pts[0][0]:
        c0, l0 = pts[0]
        return 0.0 if c0 <= 0 else l0 * (x / c0)
    if x >= pts[-1][0]:
        return pts[-1][1]
    for i in range(1, len(pts)):
        c0, l0 = pts[i - 1]
        c1, l1 = pts[i]
        if c0 <= x <= c1:
            if c1 == c0:
                return l1
            t = (x - c0) / (c1 - c0)
            return l0 + t * (l1 - l0)
    return pts[-1][1]


def litros_da_regua(
    cm: float,
    altura_cheia_cm: float,
    capacidade_l: float,
    pontos: list[tuple[float, float]] | None = None,
) -> float:
    """Usa a tabela da régua se houver ≥2 pontos; senão o cilindro."""
    if pontos:
        inter = litros_interpolado(cm, pontos)
        if inter is not None:
            return round(inter, 1)
    return round(litros_cilindro(cm, altura_cheia_cm, capacidade_l), 1)


def tabela_regua(
    altura_cheia_cm: float,
    capacidade_l: float,
    passo_cm: float = 1.0,
    pontos: list[tuple[float, float]] | None = None,
) -> list[tuple[float, float]]:
    """Tabela cm → L para colar ao lado da régua."""
    if altura_cheia_cm <= 0:
        return []
    rows: list[tuple[float, float]] = []
    cm = 0.0
    while cm <= altura_cheia_cm + 1e-9:
        rows.append((round(cm, 1), litros_da_regua(cm, altura_cheia_cm, capacidade_l, pontos)))
        cm += passo_cm
    if rows[-1][0] < altura_cheia_cm:
        rows.append(
            (
                round(altura_cheia_cm, 1),
                litros_da_regua(altura_cheia_cm, altura_cheia_cm, capacidade_l, pontos),
            )
        )
    return rows
