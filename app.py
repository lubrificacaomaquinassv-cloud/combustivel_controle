import streamlit as st
import psycopg2
import pandas as pd
from datetime import date
from io import BytesIO

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Controle de Combustível",
    page_icon="⛽",
    layout="wide",
)

# ─────────────────────────────────────────────
# CONEXÃO
# ─────────────────────────────────────────────
def get_conn():
    return psycopg2.connect(
        host=st.secrets["db"]["host"],
        port=st.secrets["db"]["port"],
        dbname=st.secrets["db"]["dbname"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        sslmode="require",
    )

# ─────────────────────────────────────────────
# COMBUSTÍVEIS
# ─────────────────────────────────────────────
COMBUSTIVEIS_COMBOIO = ["DIESEL S-500 ADITIVADO"]
COMBUSTIVEIS_POSTO   = ["DIESEL S-500 ADITIVADO", "DIESEL S-10", "GASOLINA COMUM", "ETANOL COMUM"]
TODOS_COMBUSTIVEIS   = ["DIESEL S-500 ADITIVADO", "GASOLINA COMUM", "ETANOL COMUM", "DIESEL S-10"]

# ─────────────────────────────────────────────
# CRUD — ENTRADAS
# ─────────────────────────────────────────────
def inserir_entrada(row: dict):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO combustivel_entrada
              (data, combustivel, origem, quantidade_l, valor_litro,
               fornecedor, nota_fiscal, observacao)
            VALUES (%(data)s, %(combustivel)s, %(origem)s, %(quantidade_l)s,
                    %(valor_litro)s, %(fornecedor)s, %(nota_fiscal)s, %(observacao)s)
        """, row)
        conn.commit()
        cur.close()
        conn.close()
        return True, "Entrada registrada com sucesso!"
    except Exception as e:
        return False, str(e)


def carregar_entradas(data_ini=None, data_fim=None, combustivel=None, origem=None):
    conn = get_conn()
    query = "SELECT * FROM combustivel_entrada WHERE 1=1"
    params = []
    if data_ini:
        query += " AND data >= %s"; params.append(str(data_ini))
    if data_fim:
        query += " AND data <= %s"; params.append(str(data_fim))
    if combustivel and combustivel != "Todos":
        query += " AND combustivel = %s"; params.append(combustivel)
    if origem and origem != "Todos":
        query += " AND origem = %s"; params.append(origem)
    query += " ORDER BY data DESC, id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def deletar_entrada(eid: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM combustivel_entrada WHERE id = %s", (eid,))
    conn.commit()
    cur.close()
    conn.close()

# ─────────────────────────────────────────────
# CRUD — TRANSFERÊNCIAS
# ─────────────────────────────────────────────
def inserir_transferencia(row: dict):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO combustivel_transferencia
              (data, combustivel, origem, destino, quantidade_l, observacao)
            VALUES (%(data)s, %(combustivel)s, %(origem)s, %(destino)s,
                    %(quantidade_l)s, %(observacao)s)
        """, row)
        conn.commit()
        cur.close()
        conn.close()
        return True, "Transferência registrada com sucesso!"
    except Exception as e:
        return False, str(e)


def carregar_transferencias(data_ini=None, data_fim=None):
    conn = get_conn()
    query = "SELECT * FROM combustivel_transferencia WHERE 1=1"
    params = []
    if data_ini:
        query += " AND data >= %s"; params.append(str(data_ini))
    if data_fim:
        query += " AND data <= %s"; params.append(str(data_fim))
    query += " ORDER BY data DESC, id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def deletar_transferencia(tid: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM combustivel_transferencia WHERE id = %s", (tid,))
    conn.commit()
    cur.close()
    conn.close()

# ─────────────────────────────────────────────
# CONSULTAS
# ─────────────────────────────────────────────
def carregar_saldo_geral():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM vw_saldo_combustivel_geral", conn)
    conn.close()
    return df


def carregar_consumo_comboio(data_ini=None, data_fim=None):
    conn = get_conn()
    query = "SELECT * FROM vw_consumo_diario_comboio WHERE 1=1"
    params = []
    if data_ini:
        query += " AND data >= %s"; params.append(str(data_ini))
    if data_fim:
        query += " AND data <= %s"; params.append(str(data_fim))
    query += " ORDER BY data DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def carregar_consumo_posto(data_ini=None, data_fim=None, combustivel=None):
    conn = get_conn()
    query = """
        SELECT DATE(created_at) AS data, vehicle AS frota,
               fuel_type AS combustivel,
               COALESCE(operator, '') AS operador,
               SUM(liters) AS litros_consumidos
        FROM posto WHERE 1=1
    """
    params = []
    if data_ini:
        query += " AND DATE(created_at) >= %s"; params.append(str(data_ini))
    if data_fim:
        query += " AND DATE(created_at) <= %s"; params.append(str(data_fim))
    if combustivel and combustivel != "Todos":
        query += " AND fuel_type = %s"; params.append(combustivel)
    query += " GROUP BY DATE(created_at), vehicle, fuel_type, operator ORDER BY data DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def carregar_historico_posto(data_ini=None, data_fim=None):
    conn = get_conn()
    query = """SELECT data, veiculo AS frota, combustivel,
               litros AS litros_consumidos, observacao
               FROM combustivel_historico_posto WHERE 1=1"""
    params = []
    if data_ini:
        query += " AND data >= %s"; params.append(str(data_ini))
    if data_fim:
        query += " AND data <= %s"; params.append(str(data_fim))
    query += " ORDER BY data DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def fmt_l(v):
    try:
        return f"{v:,.2f} L".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00 L"

def fmt_r(v):
    try:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def alerta(saldo):
    if saldo > 500: return "🟢"
    if saldo > 200: return "🟡"
    return "🔴"

def gerar_excel(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/color/96/gas-station.png", width=80)
st.sidebar.title("Controle de Combustível")
pagina = st.sidebar.radio("Menu", [
    "📊 Saldo Geral",
    "⛽ Lançar Entrada",
    "🔄 Transferência",
    "🚛 Consumo Comboio",
    "🏪 Consumo Posto",
    "📋 Histórico Entradas",
    "📋 Histórico Transferências",
    "📜 Histórico Planilha Posto",
])

# ═══════════════════════════════════════════
# SALDO GERAL
# ═══════════════════════════════════════════
if pagina == "📊 Saldo Geral":
    st.title("📊 Saldo Geral de Combustível")
    st.divider()

    df = carregar_saldo_geral()
    if df.empty:
        st.info("Lance entradas para calcular o saldo.")
    else:
        for _, row in df.iterrows():
            origem  = row["origem"]
            comb    = row["combustivel"]
            entrada = float(row["total_entrada_l"] or 0)
            saida   = float(row["total_saida_l"]   or 0)
            saldo   = float(row["saldo_litros"]     or 0)
            with st.container(border=True):
                st.markdown(f"### {alerta(saldo)} {origem} — {comb}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Entrada", fmt_l(entrada))
                c2.metric("Total Saída",   fmt_l(saida))
                c3.metric("Saldo Atual",   fmt_l(saldo),
                          delta=f"{saldo:+.0f} L".replace(".", ","))

    st.caption(f"Atualizado em: {date.today().strftime('%d/%m/%Y')}")

# ═══════════════════════════════════════════
# LANÇAR ENTRADA
# ═══════════════════════════════════════════
elif pagina == "⛽ Lançar Entrada":
    st.title("⛽ Lançar Entrada de Combustível")
    st.divider()

    with st.form("form_entrada", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_ent   = st.date_input("📅 Data", value=date.today())
            origem     = st.selectbox("📍 Destino", ["COMBOIO", "POSTO"])
            if origem == "COMBOIO":
                combustivel = st.selectbox("⛽ Combustível", COMBUSTIVEIS_COMBOIO)
            else:
                combustivel = st.selectbox("⛽ Combustível", COMBUSTIVEIS_POSTO)
            quantidade = st.number_input("💧 Quantidade (litros)", min_value=0.0, step=0.01, format="%.2f")
        with col2:
            valor_litro = st.number_input("💰 Valor por Litro (R$)", min_value=0.0, step=0.001, format="%.4f")
            if quantidade > 0 and valor_litro > 0:
                st.metric("💵 Valor Total", fmt_r(quantidade * valor_litro))
            fornecedor  = st.text_input("🏢 Fornecedor")
            nota_fiscal = st.text_input("📄 Nota Fiscal")
        observacao = st.text_area("📝 Observação", height=60)
        submitted  = st.form_submit_button("✅ Registrar Entrada", use_container_width=True, type="primary")

    if submitted:
        if quantidade <= 0:
            st.error("⚠️ Informe a quantidade de litros.")
        else:
            ok, msg = inserir_entrada({
                "data":         str(data_ent),
                "combustivel":  combustivel,
                "origem":       origem,
                "quantidade_l": quantidade,
                "valor_litro":  valor_litro,
                "fornecedor":   fornecedor.strip().upper() or None,
                "nota_fiscal":  nota_fiscal.strip() or None,
                "observacao":   observacao.strip() or None,
            })
            if ok:
                st.success(f"✅ {msg}")
                st.balloons()
            else:
                st.error(f"❌ {msg}")

# ═══════════════════════════════════════════
# TRANSFERÊNCIA
# ═══════════════════════════════════════════
elif pagina == "🔄 Transferência":
    st.title("🔄 Transferência de Combustível")
    st.divider()
    st.info("Registre movimentação entre POSTO e COMBOIO em qualquer direção.")

    with st.form("form_transf", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_t   = st.date_input("📅 Data", value=date.today())
            origem_t = st.selectbox("📤 Origem",  ["POSTO", "COMBOIO"])
            destino_t = "COMBOIO" if origem_t == "POSTO" else "POSTO"
            st.markdown(f"**📥 Destino:** `{destino_t}`")
        with col2:
            if origem_t == "COMBOIO":
                comb_t = st.selectbox("⛽ Combustível", COMBUSTIVEIS_COMBOIO)
            else:
                comb_t = st.selectbox("⛽ Combustível", COMBUSTIVEIS_POSTO)
            qtd_t = st.number_input("💧 Quantidade (litros)", min_value=0.0, step=0.01, format="%.2f")
        obs_t    = st.text_area("📝 Observação", height=60)
        submitted = st.form_submit_button("✅ Registrar Transferência", use_container_width=True, type="primary")

    if submitted:
        if qtd_t <= 0:
            st.error("⚠️ Informe a quantidade de litros.")
        else:
            ok, msg = inserir_transferencia({
                "data":         str(data_t),
                "combustivel":  comb_t,
                "origem":       origem_t,
                "destino":      destino_t,
                "quantidade_l": qtd_t,
                "observacao":   obs_t.strip() or None,
            })
            if ok:
                st.success(f"✅ {msg} | {fmt_l(qtd_t)} de {origem_t} → {destino_t}")
                st.balloons()
            else:
                st.error(f"❌ {msg}")

# ═══════════════════════════════════════════
# CONSUMO COMBOIO
# ═══════════════════════════════════════════
elif pagina == "🚛 Consumo Comboio":
    st.title("🚛 Consumo — Comboio")
    st.divider()

    # ── RELATÓRIO DE HOJE ──────────────────
    with st.container(border=True):
        st.markdown("### 📤 Relatório Comboio — Hoje")
        df_hoje = carregar_consumo_comboio(date.today(), date.today())
        if df_hoje.empty:
            st.info("Nenhum abastecimento registrado hoje.")
        else:
            total_hoje = df_hoje["litros_consumidos"].sum()
            c1, c2 = st.columns(2)
            c1.metric("Total Hoje", fmt_l(total_hoje))
            c2.metric("Frotas Abastecidas", df_hoje["frota"].nunique())
            st.dataframe(
                df_hoje.rename(columns={"data": "Data", "frota": "Frota",
                                        "litros_consumidos": "Litros"}),
                use_container_width=True, hide_index=True,
            )
            excel_hoje = gerar_excel(df_hoje.rename(columns={
                "data": "Data", "frota": "Frota", "litros_consumidos": "Litros (L)"
            }))
            st.download_button(
                "⬇️ Baixar Relatório de Hoje — Comboio",
                data=excel_hoje,
                file_name=f"relatorio_comboio_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )

    st.divider()

    # ── FILTRO PERSONALIZADO ───────────────
    st.markdown("### 🔍 Consulta por Período")
    with st.expander("Filtros", expanded=False):
        c1, c2 = st.columns(2)
        with c1: f_ini = st.date_input("Data início", value=None)
        with c2: f_fim = st.date_input("Data fim",    value=None)

    df = carregar_consumo_comboio(f_ini, f_fim)
    if not df.empty:
        m1, m2 = st.columns(2)
        m1.metric("Total Litros", fmt_l(df["litros_consumidos"].sum()))
        m2.metric("Registros",    len(df))

        st.dataframe(
            df.rename(columns={"data": "Data", "frota": "Frota",
                                "litros_consumidos": "Litros"}),
            use_container_width=True, hide_index=True,
        )

        st.subheader("🚛 Consumo por Frota")
        por_frota = df.groupby("frota")["litros_consumidos"].sum().reset_index().sort_values("litros_consumidos", ascending=False)
        st.bar_chart(por_frota.set_index("frota"))

        st.subheader("📅 Consumo Diário")
        por_dia = df.groupby("data")["litros_consumidos"].sum().reset_index()
        st.line_chart(por_dia.set_index("data"))

        excel_per = gerar_excel(df.rename(columns={
            "data": "Data", "frota": "Frota", "litros_consumidos": "Litros (L)"
        }))
        st.download_button(
            "⬇️ Exportar Período — Comboio",
            data=excel_per,
            file_name=f"comboio_{f_ini}_{f_fim}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ═══════════════════════════════════════════
# CONSUMO POSTO
# ═══════════════════════════════════════════
elif pagina == "🏪 Consumo Posto":
    st.title("🏪 Consumo — Posto")
    st.divider()

    # ── RELATÓRIO DE HOJE ──────────────────
    with st.container(border=True):
        st.markdown("### 📤 Relatório Posto — Hoje")
        df_hoje = carregar_consumo_posto(date.today(), date.today())
        if df_hoje.empty:
            st.info("Nenhum abastecimento registrado hoje.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Diesel",   fmt_l(df_hoje[df_hoje["combustivel"].str.contains("diesel", case=False, na=False)]["litros_consumidos"].sum()))
            c2.metric("Total Gasolina", fmt_l(df_hoje[df_hoje["combustivel"].str.contains("gasolina", case=False, na=False)]["litros_consumidos"].sum()))
            c3.metric("Frotas",         df_hoje["frota"].nunique())

            st.dataframe(
                df_hoje.rename(columns={"data": "Data", "frota": "Frota",
                                        "combustivel": "Combustível",
                                        "litros_consumidos": "Litros"}),
                use_container_width=True, hide_index=True,
            )
            excel_hoje = gerar_excel(df_hoje.rename(columns={
                "data": "Data", "frota": "Frota",
                "combustivel": "Combustível", "litros_consumidos": "Litros (L)"
            }))
            st.download_button(
                "⬇️ Baixar Relatório de Hoje — Posto",
                data=excel_hoje,
                file_name=f"relatorio_posto_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary",
            )

    st.divider()

    # ── FILTRO PERSONALIZADO ───────────────
    st.markdown("### 🔍 Consulta por Período")
    with st.expander("Filtros", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1: f_ini  = st.date_input("Data início", value=None)
        with c2: f_fim  = st.date_input("Data fim",    value=None)
        with c3: f_comb = st.selectbox("Combustível", ["Todos"] + TODOS_COMBUSTIVEIS)

    df = carregar_consumo_posto(f_ini, f_fim, f_comb)
    if not df.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Diesel",   fmt_l(df[df["combustivel"].str.contains("diesel", case=False, na=False)]["litros_consumidos"].sum()))
        m2.metric("Total Gasolina", fmt_l(df[df["combustivel"].str.contains("gasolina", case=False, na=False)]["litros_consumidos"].sum()))
        m3.metric("Registros",      len(df))

        st.dataframe(
            df.rename(columns={"data": "Data", "frota": "Frota",
                                "combustivel": "Combustível",
                                "litros_consumidos": "Litros"}),
            use_container_width=True, hide_index=True,
        )

        st.subheader("🏪 Consumo por Frota")
        por_frota = df.groupby(["frota", "combustivel"])["litros_consumidos"].sum().reset_index()
        pivot = por_frota.pivot(index="frota", columns="combustivel", values="litros_consumidos").fillna(0)
        st.bar_chart(pivot)

        excel_per = gerar_excel(df.rename(columns={
            "data": "Data", "frota": "Frota",
            "combustivel": "Combustível", "litros_consumidos": "Litros (L)"
        }))
        st.download_button(
            "⬇️ Exportar Período — Posto",
            data=excel_per,
            file_name=f"posto_{f_ini}_{f_fim}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# ═══════════════════════════════════════════
# HISTÓRICO ENTRADAS
# ═══════════════════════════════════════════
elif pagina == "📋 Histórico Entradas":
    st.title("📋 Histórico de Entradas")
    st.divider()

    with st.expander("🔍 Filtros", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1: f_ini  = st.date_input("Data início", value=None)
        with c2: f_fim  = st.date_input("Data fim",    value=None)
        with c3: f_comb = st.selectbox("Combustível",  ["Todos"] + TODOS_COMBUSTIVEIS)
        with c4: f_orig = st.selectbox("Origem",       ["Todos", "COMBOIO", "POSTO"])

    df = carregar_entradas(f_ini, f_fim,
                           f_comb if f_comb != "Todos" else None,
                           f_orig if f_orig != "Todos" else None)
    if df.empty:
        st.info("Nenhuma entrada encontrada.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Entradas", len(df))
        m2.metric("Total Litros",   fmt_l(df["quantidade_l"].sum()))
        m3.metric("Valor Total",    fmt_r(df["valor_total"].sum()))

        df_show = df.copy()
        df_show["quantidade_l"] = df_show["quantidade_l"].apply(fmt_l)
        df_show["valor_litro"]  = df_show["valor_litro"].apply(lambda v: f"R$ {v:.4f}")
        df_show["valor_total"]  = df_show["valor_total"].apply(fmt_r)
        df_show = df_show.rename(columns={
            "id": "ID", "data": "Data", "combustivel": "Combustível",
            "origem": "Origem", "quantidade_l": "Litros",
            "valor_litro": "R$/L", "valor_total": "Total",
            "fornecedor": "Fornecedor", "nota_fiscal": "NF",
            "observacao": "Observação",
        })
        st.dataframe(
            df_show[["ID", "Data", "Combustível", "Origem", "Litros",
                      "R$/L", "Total", "Fornecedor", "NF", "Observação"]],
            use_container_width=True, hide_index=True,
        )

        st.divider()
        st.subheader("🗑️ Excluir Entrada")
        ids = df["id"].tolist()
        sel = st.selectbox("Selecione o ID", ids)
        reg = df[df["id"] == sel].iloc[0]
        st.caption(f"Data: {reg['data']} | {reg['combustivel']} | {reg['origem']} | {fmt_l(reg['quantidade_l'])}")
        if st.button("🗑️ Confirmar Exclusão", type="primary"):
            deletar_entrada(sel)
            st.success("Entrada excluída.")
            st.rerun()

        excel = gerar_excel(df)
        st.download_button("⬇️ Exportar Excel", data=excel,
            file_name=f"entradas_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ═══════════════════════════════════════════
# HISTÓRICO TRANSFERÊNCIAS
# ═══════════════════════════════════════════
elif pagina == "📋 Histórico Transferências":
    st.title("📋 Histórico de Transferências")
    st.divider()

    with st.expander("🔍 Filtros", expanded=True):
        c1, c2 = st.columns(2)
        with c1: f_ini = st.date_input("Data início", value=None)
        with c2: f_fim = st.date_input("Data fim",    value=None)

    df = carregar_transferencias(f_ini, f_fim)
    if df.empty:
        st.info("Nenhuma transferência encontrada.")
    else:
        m1, m2 = st.columns(2)
        m1.metric("Total Transferências", len(df))
        m2.metric("Total Litros",         fmt_l(df["quantidade_l"].sum()))

        df_show = df.copy()
        df_show["quantidade_l"] = df_show["quantidade_l"].apply(fmt_l)
        df_show = df_show.rename(columns={
            "id": "ID", "data": "Data", "combustivel": "Combustível",
            "origem": "Origem", "destino": "Destino",
            "quantidade_l": "Litros", "observacao": "Observação",
        })
        st.dataframe(
            df_show[["ID", "Data", "Combustível", "Origem", "Destino",
                      "Litros", "Observação"]],
            use_container_width=True, hide_index=True,
        )

        st.divider()
        st.subheader("🗑️ Excluir Transferência")
        ids = df["id"].tolist()
        sel = st.selectbox("Selecione o ID", ids)
        reg = df[df["id"] == sel].iloc[0]
        st.caption(f"Data: {reg['data']} | {reg['combustivel']} | {reg['origem']} → {reg['destino']} | {fmt_l(reg['quantidade_l'])}")
        if st.button("🗑️ Confirmar Exclusão", type="primary"):
            deletar_transferencia(sel)
            st.success("Transferência excluída.")
            st.rerun()

# ═══════════════════════════════════════════
# HISTÓRICO PLANILHA POSTO
# ═══════════════════════════════════════════
elif pagina == "📜 Histórico Planilha Posto":
    st.title("📜 Histórico Posto — Importado da Planilha")
    st.divider()
    st.info("Saídas históricas importadas da planilha (Jan/2025 – Mai/2026)")

    with st.expander("🔍 Filtros", expanded=True):
        c1, c2 = st.columns(2)
        with c1: f_ini = st.date_input("Data início", value=None)
        with c2: f_fim = st.date_input("Data fim",    value=None)

    df = carregar_historico_posto(f_ini, f_fim)
    if df.empty:
        st.info("Nenhum registro encontrado.")
    else:
        m1, m2 = st.columns(2)
        m1.metric("Total Registros", len(df))
        m2.metric("Total Litros",    fmt_l(df["litros_consumidos"].sum()))

        st.dataframe(
            df.rename(columns={"data": "Data", "frota": "Veículo",
                                "combustivel": "Combustível",
                                "litros_consumidos": "Litros",
                                "observacao": "Observação"}),
            use_container_width=True, hide_index=True,
        )

        st.subheader("🚜 Consumo por Veículo (Top 15)")
        por_veiculo = df.groupby("frota")["litros_consumidos"].sum().reset_index().sort_values("litros_consumidos", ascending=False).head(15)
        st.bar_chart(por_veiculo.set_index("frota"))

        excel = gerar_excel(df.rename(columns={
            "data": "Data", "frota": "Veículo",
            "combustivel": "Combustível",
            "litros_consumidos": "Litros (L)",
            "observacao": "Observação"
        }))
        st.download_button("⬇️ Exportar Excel", data=excel,
            file_name=f"historico_posto_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
