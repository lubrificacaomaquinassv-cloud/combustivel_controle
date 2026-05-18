import streamlit as st
import psycopg2
import pandas as pd
from datetime import date

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Controle de Combustível",
    page_icon="⛽",
    layout="wide",
)

# ─────────────────────────────────────────────
# CONEXÃO SUPABASE
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
# CRUD
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
        query += " AND data >= %s"
        params.append(str(data_ini))
    if data_fim:
        query += " AND data <= %s"
        params.append(str(data_fim))
    if combustivel and combustivel != "Todos":
        query += " AND combustivel = %s"
        params.append(combustivel)
    if origem and origem != "Todos":
        query += " AND origem = %s"
        params.append(origem)
    query += " ORDER BY data DESC, id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


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
        query += " AND data >= %s"
        params.append(str(data_ini))
    if data_fim:
        query += " AND data <= %s"
        params.append(str(data_fim))
    query += " ORDER BY data DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def carregar_consumo_posto(data_ini=None, data_fim=None):
    conn = get_conn()
    query = """
        SELECT
            DATE(created_at)  AS data,
            vehicle           AS frota,
            fuel_type         AS combustivel,
            SUM(liters)       AS litros_consumidos
        FROM posto
        WHERE 1=1
    """
    params = []
    if data_ini:
        query += " AND DATE(created_at) >= %s"
        params.append(str(data_ini))
    if data_fim:
        query += " AND DATE(created_at) <= %s"
        params.append(str(data_fim))
    query += " GROUP BY DATE(created_at), vehicle, fuel_type ORDER BY data DESC"
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
# HELPERS
# ─────────────────────────────────────────────
def fmt_litros(v):
    try:
        return f"{v:,.2f} L".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00 L"

def fmt_moeda(v):
    try:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/color/96/gas-station.png", width=80)
st.sidebar.title("Controle de Combustível")
pagina = st.sidebar.radio(
    "Menu",
    ["📊 Saldo Geral", "⛽ Lançar Entrada", "🚛 Consumo Comboio",
     "🏪 Consumo Posto", "📋 Histórico Entradas"],
)

# ═══════════════════════════════════════════
# SALDO GERAL
# ═══════════════════════════════════════════
if pagina == "📊 Saldo Geral":
    st.title("📊 Saldo Geral de Combustível")
    st.divider()

    df = carregar_saldo_geral()

    if df.empty:
        st.info("Nenhum dado encontrado. Lance entradas para calcular o saldo.")
    else:
        for _, row in df.iterrows():
            origem     = row["origem"]
            comb       = row["combustivel"]
            entrada    = float(row["total_entrada_l"] or 0)
            saida      = float(row["total_saida_l"] or 0)
            saldo      = float(row["saldo_litros"] or 0)

            cor = "🟢" if saldo > 500 else "🟡" if saldo > 200 else "🔴"

            with st.container(border=True):
                st.markdown(f"### {cor} {origem} — {comb}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Entrada", fmt_litros(entrada))
                c2.metric("Total Saída",   fmt_litros(saida))
                c3.metric("Saldo Atual",   fmt_litros(saldo),
                          delta=f"{saldo:+.0f} L".replace(".", ","))

    st.divider()
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
            data_ent    = st.date_input("📅 Data", value=date.today())
            combustivel = st.selectbox("⛽ Combustível", ["DIESEL", "GASOLINA"])
            origem      = st.selectbox("📍 Destino", ["COMBOIO", "POSTO"])
            quantidade  = st.number_input("💧 Quantidade (litros)", min_value=0.0, step=0.01, format="%.2f")

        with col2:
            valor_litro  = st.number_input("💰 Valor por Litro (R$)", min_value=0.0, step=0.001, format="%.4f")
            if quantidade > 0 and valor_litro > 0:
                st.metric("💵 Valor Total", fmt_moeda(quantidade * valor_litro))
            fornecedor   = st.text_input("🏢 Fornecedor")
            nota_fiscal  = st.text_input("📄 Nota Fiscal")

        observacao = st.text_area("📝 Observação", height=60)

        submitted = st.form_submit_button("✅ Registrar Entrada", use_container_width=True, type="primary")

    if submitted:
        if quantidade <= 0:
            st.error("⚠️ Informe a quantidade de litros.")
        elif valor_litro <= 0:
            st.error("⚠️ Informe o valor por litro.")
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
# CONSUMO COMBOIO
# ═══════════════════════════════════════════
elif pagina == "🚛 Consumo Comboio":
    st.title("🚛 Consumo Diário — Comboio (Diesel)")
    st.divider()

    with st.expander("🔍 Filtros", expanded=True):
        c1, c2 = st.columns(2)
        with c1: f_ini = st.date_input("Data início", value=None)
        with c2: f_fim = st.date_input("Data fim",    value=None)

    df = carregar_consumo_comboio(f_ini, f_fim)

    if df.empty:
        st.info("Nenhum consumo encontrado.")
    else:
        total = df["litros_consumidos"].sum()
        m1, m2 = st.columns(2)
        m1.metric("Total Litros Consumidos", fmt_litros(total))
        m2.metric("Registros",               len(df))

        st.dataframe(
            df.rename(columns={
                "data": "Data", "frota": "Frota",
                "litros_consumidos": "Litros",
            }),
            use_container_width=True,
            hide_index=True,
        )

        # Gráfico por frota
        st.subheader("🚛 Consumo Total por Frota")
        por_frota = df.groupby("frota")["litros_consumidos"].sum().reset_index().sort_values("litros_consumidos", ascending=False)
        st.bar_chart(por_frota.set_index("frota"))

        # Gráfico por dia
        st.subheader("📅 Consumo Diário Total")
        por_dia = df.groupby("data")["litros_consumidos"].sum().reset_index()
        st.line_chart(por_dia.set_index("data"))

# ═══════════════════════════════════════════
# CONSUMO POSTO
# ═══════════════════════════════════════════
elif pagina == "🏪 Consumo Posto":
    st.title("🏪 Consumo — Posto")
    st.divider()

    with st.expander("🔍 Filtros", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1: f_ini  = st.date_input("Data início", value=None)
        with c2: f_fim  = st.date_input("Data fim",    value=None)
        with c3: f_comb = st.selectbox("Combustível",  ["Todos", "DIESEL", "GASOLINA"])

    df = carregar_consumo_posto(f_ini, f_fim)
    if f_comb != "Todos":
        df = df[df["combustivel"] == f_comb]

    if df.empty:
        st.info("Nenhum consumo encontrado.")
    else:
        total_diesel   = df[df["combustivel"] == "DIESEL"]["litros_consumidos"].sum()
        total_gasolina = df[df["combustivel"] == "GASOLINA"]["litros_consumidos"].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Diesel",   fmt_litros(total_diesel))
        m2.metric("Total Gasolina", fmt_litros(total_gasolina))
        m3.metric("Registros",      len(df))

        st.dataframe(
            df.rename(columns={
                "data": "Data", "frota": "Frota",
                "combustivel": "Combustível",
                "litros_consumidos": "Litros",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("🏪 Consumo por Frota")
        por_frota = df.groupby(["frota", "combustivel"])["litros_consumidos"].sum().reset_index()
        st.bar_chart(por_frota.pivot(index="frota", columns="combustivel", values="litros_consumidos").fillna(0))

# ═══════════════════════════════════════════
# HISTÓRICO ENTRADAS
# ═══════════════════════════════════════════
elif pagina == "📋 Histórico Entradas":
    st.title("📋 Histórico de Entradas")
    st.divider()

    with st.expander("🔍 Filtros", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1: f_ini  = st.date_input("Data início",  value=None)
        with c2: f_fim  = st.date_input("Data fim",     value=None)
        with c3: f_comb = st.selectbox("Combustível",   ["Todos", "DIESEL", "GASOLINA"])
        with c4: f_orig = st.selectbox("Origem",        ["Todos", "COMBOIO", "POSTO"])

    df = carregar_entradas(f_ini, f_fim,
                           f_comb if f_comb != "Todos" else None,
                           f_orig if f_orig != "Todos" else None)

    if df.empty:
        st.info("Nenhuma entrada encontrada.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Entradas",  len(df))
        m2.metric("Total Litros",    fmt_litros(df["quantidade_l"].sum()))
        m3.metric("Valor Total",     fmt_moeda(df["valor_total"].sum()))

        df_show = df.copy()
        df_show["quantidade_l"] = df_show["quantidade_l"].apply(fmt_litros)
        df_show["valor_litro"]  = df_show["valor_litro"].apply(lambda v: f"R$ {v:.4f}")
        df_show["valor_total"]  = df_show["valor_total"].apply(fmt_moeda)
        df_show = df_show.rename(columns={
            "id": "ID", "data": "Data", "combustivel": "Combustível",
            "origem": "Origem", "quantidade_l": "Qtd Litros",
            "valor_litro": "R$/Litro", "valor_total": "Total",
            "fornecedor": "Fornecedor", "nota_fiscal": "NF",
            "observacao": "Observação",
        })
        st.dataframe(
            df_show[["ID", "Data", "Combustível", "Origem", "Qtd Litros",
                      "R$/Litro", "Total", "Fornecedor", "NF", "Observação"]],
            use_container_width=True,
            hide_index=True,
        )

        # Excluir
        st.divider()
        st.subheader("🗑️ Excluir Entrada")
        ids = df["id"].tolist()
        sel = st.selectbox("Selecione o ID para excluir", ids)
        if st.button("🗑️ Excluir", type="primary"):
            deletar_entrada(sel)
            st.success("Entrada excluída.")
            st.rerun()

        # Export
        df.to_excel("/tmp/combustivel_entradas.xlsx", index=False)
        with open("/tmp/combustivel_entradas.xlsx", "rb") as f:
            st.download_button(
                "⬇️ Exportar Excel",
                data=f,
                file_name=f"combustivel_entradas_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
