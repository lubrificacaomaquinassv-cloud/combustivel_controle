"""Motor de conciliação — recalcula saldos a partir das tabelas brutas e compara com views."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any

from . import db

TZ = "America/Campo_Grande"
TOL_L = 0.05  # tolerância litros (arredondamento)


@dataclass
class LinhaConciliacao:
    local: str
    combustivel: str
    data_referencia: date | None
    referencia: str
    entrada_l: float
    consumo_l: float
    transferencia_l: float
    total_saidas_l: float
    saldo_calculado: float
    saldo_view: float | None
    diferenca_l: float
    ok: bool
    detalhes: dict[str, Any] = field(default_factory=dict)


@dataclass
class SapResumo:
    origem: str
    total: int
    baixado: int
    pendente: int
    pct_baixado: float


@dataclass
class AuditoriaCompleta:
    gerado_em: str
    conciliacao_s500: list[LinhaConciliacao]
    tanques: list[dict]
    sap: list[SapResumo]
    alertas: list[str]
    entradas: list[dict]
    transferencias: list[dict]
    ok_geral: bool


def _f(v) -> float:
    return float(v or 0)


def _ok(a: float, b: float) -> bool:
    return abs(a - b) <= TOL_L


def _view_row(view: str) -> dict | None:
    return db.query_one(f"SELECT * FROM {view} LIMIT 1")


def conciliar_posto_s500() -> LinhaConciliacao:
    """POSTO S-500: última NF − consumo PWA − transf. comboio (desde data NF)."""
    nf = db.query_one(
        """
        SELECT id, data, quantidade_l, nota_fiscal
        FROM combustivel_entrada
        WHERE upper(coalesce(origem, '')) = 'POSTO'
          AND combustivel ILIKE '%%S-500%%'
        ORDER BY data DESC, id DESC
        LIMIT 1
        """
    )
    if not nf:
        return LinhaConciliacao(
            local="POSTO",
            combustivel="DIESEL S-500 ADITIVADO",
            data_referencia=None,
            referencia="sem NF",
            entrada_l=0,
            consumo_l=0,
            transferencia_l=0,
            total_saidas_l=0,
            saldo_calculado=0,
            saldo_view=None,
            diferenca_l=0,
            ok=False,
            detalhes={"erro": "Nenhuma NF S-500 encontrada"},
        )

    dt = nf["data"]
    consumo = db.query_one(
        """
        SELECT coalesce(sum(quantidade_litros), 0) AS v
        FROM abastecimentos.abastecimentos
        WHERE origem = 'POSTO'
          AND tipo_combustivel ILIKE '%%S-500%%'
          AND created_at::date >= %s
        """,
        [dt],
    )
    transf = db.query_one(
        """
        SELECT coalesce(sum(quantidade_l), 0) AS v
        FROM combustivel_transferencia
        WHERE upper(coalesce(origem, '')) = 'POSTO'
          AND upper(coalesce(destino, '')) = 'COMBOIO'
          AND combustivel ILIKE '%%S-500%%'
          AND data >= %s
        """,
        [dt],
    )
    entrada = _f(nf["quantidade_l"])
    cons = _f(consumo["v"])
    trf = _f(transf["v"])
    saldo_calc = entrada - cons - trf

    view = _view_row("vw_saldo_posto_v2")
    saldo_view = _f(view["saldo_litros"]) if view else None

    return LinhaConciliacao(
        local="POSTO",
        combustivel="DIESEL S-500 ADITIVADO",
        data_referencia=dt,
        referencia=f"NF {nf.get('nota_fiscal') or nf['id']}",
        entrada_l=entrada,
        consumo_l=cons,
        transferencia_l=trf,
        total_saidas_l=cons + trf,
        saldo_calculado=saldo_calc,
        saldo_view=saldo_view,
        diferenca_l=(saldo_calc - saldo_view) if saldo_view is not None else 0,
        ok=saldo_view is not None and _ok(saldo_calc, saldo_view),
        detalhes={
            "nf_id": nf["id"],
            "view_entrada": _f(view.get("entrada_l")) if view else None,
            "view_consumo": _f(view.get("saida_posto_l")) if view else None,
            "view_transf": _f(view.get("transferencia_comboio_l")) if view else None,
        },
    )


def conciliar_comboio_s500() -> LinhaConciliacao:
    """COMBOIO S-500: ciclo = transf. desde penúltima carga; saídas comboio_v2 no ciclo."""
    penult = db.query_one(
        """
        SELECT data, quantidade_l, id
        FROM combustivel_transferencia
        WHERE upper(coalesce(origem, '')) = 'POSTO'
          AND upper(coalesce(destino, '')) = 'COMBOIO'
          AND combustivel ILIKE '%%S-500%%'
        ORDER BY data DESC, id DESC
        OFFSET 1 LIMIT 1
        """
    )
    if not penult:
        # só uma transferência — ciclo desde ela
        ciclo_desde = db.query_one(
            """
            SELECT min(data) AS d FROM combustivel_transferencia
            WHERE upper(coalesce(origem, '')) = 'POSTO'
              AND upper(coalesce(destino, '')) = 'COMBOIO'
              AND combustivel ILIKE '%%S-500%%'
            """
        )
        dt_ciclo = ciclo_desde["d"] if ciclo_desde else date.today()
        entrada_ant = 0.0
    else:
        dt_ciclo = penult["data"]
        entrada_ant = _f(penult["quantidade_l"])

    ciclo = db.query_one(
        """
        SELECT coalesce(sum(quantidade_l), 0) AS entrada_l,
               count(*) AS qtd
        FROM combustivel_transferencia
        WHERE upper(coalesce(origem, '')) = 'POSTO'
          AND upper(coalesce(destino, '')) = 'COMBOIO'
          AND combustivel ILIKE '%%S-500%%'
          AND data >= %s
        """,
        [dt_ciclo],
    )
    saidas = db.query_one(
        """
        SELECT coalesce(sum(liters), 0) AS v
        FROM comboio_v2
        WHERE (created_at AT TIME ZONE %s)::date >= %s
        """,
        [TZ, dt_ciclo],
    )
    legado = db.query_one(
        """
        SELECT coalesce(sum(liters), 0) AS v
        FROM comboio
        WHERE (created_at AT TIME ZONE %s)::date >= %s
        """,
        [TZ, dt_ciclo],
    )

    entrada = _f(ciclo["entrada_l"])
    cons = _f(saidas["v"]) + _f(legado["v"])
    saldo_calc = entrada - cons

    view = _view_row("vw_saldo_comboio")
    saldo_view = _f(view["saldo_litros"]) if view else None

    return LinhaConciliacao(
        local="COMBOIO",
        combustivel="DIESEL S-500 ADITIVADO",
        data_referencia=dt_ciclo,
        referencia=f"ciclo desde {dt_ciclo} ({int(ciclo['qtd'])} transf.)",
        entrada_l=entrada,
        consumo_l=cons,
        transferencia_l=0,
        total_saidas_l=cons,
        saldo_calculado=saldo_calc,
        saldo_view=saldo_view,
        diferenca_l=(saldo_calc - saldo_view) if saldo_view is not None else 0,
        ok=saldo_view is not None and _ok(saldo_calc, saldo_view),
        detalhes={
            "entrada_anterior_l": entrada_ant,
            "qtd_transferencias_ciclo": int(ciclo["qtd"]),
            "saida_comboio_v2_l": _f(saidas["v"]),
            "saida_legado_l": _f(legado["v"]),
            "view_entrada": _f(view.get("total_entrada_l")) if view else None,
            "view_saida": _f(view.get("total_saida_l")) if view else None,
        },
    )


def conciliar_tanque(view: str, local: str, combustivel: str) -> LinhaConciliacao | None:
    """Concilia tanques S-10 e gasolina (entrada NF − consumo PWA)."""
    if "s10" in view:
        nf = db.query_one(
            """
            SELECT data, quantidade_l, nota_fiscal
            FROM combustivel_entrada
            WHERE upper(coalesce(origem, '')) = 'POSTO'
              AND combustivel ILIKE '%%S-10%%'
            ORDER BY data DESC, id DESC LIMIT 1
            """
        )
        if not nf:
            return None
        cons = db.query_one(
            """
            SELECT coalesce(sum(quantidade_litros), 0) AS v
            FROM abastecimentos.abastecimentos
            WHERE origem = 'POSTO'
              AND tipo_combustivel ILIKE '%%S-10%%'
              AND (created_at AT TIME ZONE %s)::date >= %s
              AND upper(coalesce(veiculo_codigo, '')) NOT LIKE '%%AJUSTE%%'
            """,
            [TZ, nf["data"]],
        )
    else:
        nf = db.query_one(
            """
            SELECT data, quantidade_l, nota_fiscal
            FROM combustivel_entrada
            WHERE upper(coalesce(origem, '')) = 'POSTO'
              AND combustivel ILIKE '%%GASOLINA%%'
            ORDER BY data DESC, id DESC LIMIT 1
            """
        )
        if not nf:
            return None
        cons = db.query_one(
            """
            SELECT coalesce(sum(quantidade_litros), 0) AS v
            FROM abastecimentos.abastecimentos
            WHERE origem = 'POSTO'
              AND tipo_combustivel ILIKE '%%GASOLINA%%'
              AND created_at::date >= %s
            """,
            [nf["data"]],
        )

    entrada = _f(nf["quantidade_l"])
    consumo = _f(cons["v"])
    saldo_calc = entrada - consumo
    view_row = _view_row(view)
    if view == "vw_saldo_gasolina_posto":
        saldo_view = _f(view_row.get("saldo_estimado")) if view_row else None
    else:
        saldo_view = _f(view_row.get("saldo_litros")) if view_row else None

    return LinhaConciliacao(
        local=local,
        combustivel=combustivel,
        data_referencia=nf["data"],
        referencia=f"NF {nf.get('nota_fiscal') or ''}",
        entrada_l=entrada,
        consumo_l=consumo,
        transferencia_l=0,
        total_saidas_l=consumo,
        saldo_calculado=saldo_calc,
        saldo_view=saldo_view,
        diferenca_l=(saldo_calc - saldo_view) if saldo_view is not None else 0,
        ok=saldo_view is not None and _ok(saldo_calc, saldo_view),
    )


def resumo_sap() -> list[SapResumo]:
    rows = []
    for origem, sql in (
        (
            "POSTO",
            """
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE coalesce(status_sap,'PENDENTE')='BAIXADO') AS baixado
            FROM abastecimentos.abastecimentos WHERE origem='POSTO'
            """,
        ),
        (
            "COMBOIO_V2",
            """
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE coalesce(status_sap,'PENDENTE')='BAIXADO') AS baixado
            FROM comboio_v2
            """,
        ),
    ):
        r = db.query_one(sql)
        total = int(r["total"])
        baixado = int(r["baixado"])
        pend = total - baixado
        rows.append(
            SapResumo(
                origem=origem,
                total=total,
                baixado=baixado,
                pendente=pend,
                pct_baixado=round(100 * baixado / total, 1) if total else 100.0,
            )
        )
    return rows


def listar_entradas(limit: int = 20) -> list[dict]:
    return db.query_all(
        """
        SELECT id, data, combustivel, origem, quantidade_l, nota_fiscal, fornecedor, observacao
        FROM combustivel_entrada
        ORDER BY data DESC, id DESC
        LIMIT %s
        """,
        [limit],
    )


def listar_transferencias(limit: int = 20) -> list[dict]:
    return db.query_all(
        """
        SELECT id, data, combustivel, origem, destino, quantidade_l, observacao
        FROM combustivel_transferencia
        ORDER BY data DESC, id DESC
        LIMIT %s
        """,
        [limit],
    )


def tanques_oficiais() -> list[dict]:
    return db.query_all("SELECT origem, combustivel, total_entrada_l, total_saida_l, saldo_litros FROM vw_saldo_combustivel_geral")


def executar_auditoria() -> AuditoriaCompleta:
    conc = [
        conciliar_posto_s500(),
        conciliar_comboio_s500(),
    ]
    for view, loc, comb in (
        ("vw_saldo_s10_posto", "POSTO", "DIESEL S-10"),
        ("vw_saldo_gasolina_posto", "POSTO", "GASOLINA COMUM"),
    ):
        linha = conciliar_tanque(view, loc, comb)
        if linha:
            conc.append(linha)

    sap = resumo_sap()
    alertas: list[str] = []
    for c in conc:
        if not c.ok:
            alertas.append(
                f"{c.local} {c.combustivel}: diferença {c.diferenca_l:+.2f} L "
                f"(calc={c.saldo_calculado:.2f} view={c.saldo_view})"
            )
    for s in sap:
        if s.pendente > 0:
            alertas.append(f"SAP {s.origem}: {s.pendente} registro(s) PENDENTE")

    ok = not alertas

    return AuditoriaCompleta(
        gerado_em=datetime.now().isoformat(timespec="seconds"),
        conciliacao_s500=[c for c in conc if "S-500" in c.combustivel],
        tanques=[{"origem": t["origem"], "combustivel": t["combustivel"], "saldo_l": _f(t["saldo_litros"])} for t in tanques_oficiais()],
        sap=sap,
        alertas=alertas,
        entradas=listar_entradas(15),
        transferencias=listar_transferencias(15),
        ok_geral=ok,
    )


def auditoria_para_dict(a: AuditoriaCompleta) -> dict:
    return {
        "gerado_em": a.gerado_em,
        "ok_geral": a.ok_geral,
        "conciliacao": [asdict(c) for c in a.conciliacao_s500 + [x for x in [
            conciliar_tanque("vw_saldo_s10_posto", "POSTO", "DIESEL S-10"),
            conciliar_tanque("vw_saldo_gasolina_posto", "POSTO", "GASOLINA COMUM"),
        ] if x]],
        "tanques": a.tanques,
        "sap": [asdict(s) for s in a.sap],
        "alertas": a.alertas,
        "entradas": a.entradas,
        "transferencias": a.transferencias,
    }
