"""API pública — usada pelo Streamlit e scripts CLI."""
from __future__ import annotations

import json
from typing import Any

import pandas as pd

from . import engine


def executar_auditoria_completa() -> dict[str, Any]:
    """Retorna dict JSON-serializável com toda a auditoria."""
    return engine.auditoria_para_dict(engine.executar_auditoria())


def resumo_conciliacao_s500() -> pd.DataFrame:
    """Tabela POSTO + COMBOIO S-500 para exibição no painel."""
    a = engine.executar_auditoria()
    rows = []
    for c in a.conciliacao_s500:
        rows.append(
            {
                "Local": c.local,
                "Combustível": c.combustivel,
                "Referência": c.referencia,
                "Entrada (L)": c.entrada_l,
                "Consumo (L)": c.consumo_l,
                "Transf. (L)": c.transferencia_l if c.transferencia_l else None,
                "Saldo calc. (L)": c.saldo_calculado,
                "Saldo view (L)": c.saldo_view,
                "Dif. (L)": c.diferenca_l,
                "Status": "OK" if c.ok else "DIVERGENTE",
            }
        )
    return pd.DataFrame(rows)


def resumo_sap_baixas() -> pd.DataFrame:
    return pd.DataFrame([vars(s) for s in engine.resumo_sap()])


def resumo_tanques() -> pd.DataFrame:
    return pd.DataFrame(engine.tanques_oficiais())


def imprimir_relatorio() -> None:
    """CLI — imprime relatório formatado."""
    data = executar_auditoria_completa()
    print("=" * 72)
    print("AUDITORIA COMBUSTÍVEL — POSTO · COMBOIO · ENTRADAS · TRANSFERÊNCIAS · SAP")
    print("=" * 72)
    print(f"Gerado: {data['gerado_em']}")
    print(f"Status geral: {'OK' if data['ok_geral'] else 'ATENÇÃO — divergências'}")
    print()

    print("--- CONCILIAÇÃO S-500 (Python vs views Supabase) ---")
    for c in data["conciliacao"]:
        st = "OK" if c["ok"] else "DIVERGENTE"
        print(
            f"  [{st}] {c['local']} | {c['combustivel']}\n"
            f"       ref: {c['referencia']}\n"
            f"       entrada={c['entrada_l']:.1f} consumo={c['consumo_l']:.1f} "
            f"transf={c['transferencia_l']:.1f} saldo_calc={c['saldo_calculado']:.1f} "
            f"saldo_view={c['saldo_view']} dif={c['diferenca_l']:+.2f} L"
        )

    print("\n--- TANQUES (vw_saldo_combustivel_geral) ---")
    for t in data["tanques"]:
        print(f"  {t['origem']:8s} {t['combustivel']:28s} {t['saldo_l']:,.1f} L")

    print("\n--- BAIXAS SAP ---")
    for s in data["sap"]:
        print(
            f"  {s['origem']:12s} total={s['total']:4d} baixado={s['baixado']:4d} "
            f"pendente={s['pendente']:4d} ({s['pct_baixado']:.1f}%)"
        )

    if data["alertas"]:
        print("\n--- ALERTAS ---")
        for al in data["alertas"]:
            print(f"  ! {al}")

    print("\n--- ÚLTIMAS ENTRADAS ---")
    for e in data["entradas"][:8]:
        print(
            f"  {e['data']} {e['origem']:6s} {e['combustivel'][:22]:22s} "
            f"{float(e['quantidade_l']):8.1f} L NF={e.get('nota_fiscal') or '-'}"
        )

    print("\n--- ÚLTIMAS TRANSFERÊNCIAS ---")
    for t in data["transferencias"][:8]:
        print(
            f"  {t['data']} {t['origem']}->{t['destino']} "
            f"{float(t['quantidade_l']):8.1f} L {t.get('observacao') or ''}"
        )

    print()
    return data


if __name__ == "__main__":
    imprimir_relatorio()
