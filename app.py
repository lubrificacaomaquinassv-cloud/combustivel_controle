import streamlit as st
import psycopg2
from sigcf_auth import exigir_acesso, logo_html
import pandas as pd
from datetime import date
from io import BytesIO

# Linha do tempo oficial — saídas do posto (planilha + PWA)
HIST_PLANILHA_INI = date(2026, 1, 1)
HIST_PLANILHA_FIM = date(2026, 5, 14)
PWA_POSTO_INI = date(2026, 5, 18)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Controle de Combustível",
    page_icon="⛽",
    layout="wide",
)

exigir_acesso("Controle de Combustível")

CAP_COMBOIO = 5000
CAP_S500 = 10000
CAP_S10 = 5000
CAP_GAS = 5000

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&display=swap');
[data-testid="stAppViewContainer"]{background:#0a1409;}
[data-testid="stSidebar"]{background:#111c10;border-right:1px solid #1e2e1c;}
[data-testid="stHeader"]{background:#0a1409;}
h1,h2,h3,h4,p,span,label{color:#e8edd0;}
h1{font-family:'Barlow Condensed',sans-serif;letter-spacing:1px;}
.stCaption,[data-testid="stCaptionContainer"] p{color:#8aab80!important;}

/* Sidebar — título e menu na cor do tema central */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{
 color:#e8edd0!important;font-family:'Barlow Condensed',sans-serif!important;}
[data-testid="stSidebar"] [data-testid="stRadio"] label,
[data-testid="stSidebar"] [data-testid="stRadio"] label span,
[data-testid="stSidebar"] [data-testid="stRadio"] label p,
[data-testid="stSidebar"] [data-testid="stRadio"] label div{
 color:#c8d8bc!important;font-family:'Barlow Condensed',sans-serif;}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) span,
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p{
 color:#e8edd0!important;}

/* Campos — fundo claro suave (sage), sem branco puro */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
[data-testid="stDateInput"] input{
 background:#dce6d2!important;color:#1a2818!important;
 border:1px solid #4a6644!important;border-radius:8px!important;}
.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus,
[data-testid="stDateInput"] input:focus{
 border-color:#6fcf60!important;box-shadow:0 0 0 1px #6fcf6044!important;}
.stTextInput input::placeholder,
.stTextArea textarea::placeholder{color:#6a7a64!important;}
div[data-baseweb="select"] > div{
 background:#dce6d2!important;border:1px solid #4a6644!important;
 color:#1a2818!important;border-radius:8px!important;}
div[data-baseweb="select"] div{color:#1a2818!important;}
div[data-baseweb="select"] svg{fill:#4a6644!important;}
ul[data-testid="stSelectboxVirtualDropdown"],
div[data-baseweb="popover"] ul{background:#e8edd0!important;}
div[data-baseweb="popover"] li{color:#1a2818!important;}
[data-testid="stNumberInput"] button{
 background:#cdd9c4!important;border-color:#4a6644!important;color:#1a2818!important;}
[data-testid="stForm"]{
 background:#0d180c!important;border:1px solid #1e2e1c!important;
 border-radius:12px;padding:12px 16px;}
[data-testid="stVerticalBlockBorderWrapper"]{
 background:#0d180c!important;border-color:#1e2e1c!important;}

div[data-testid="stMetric"]{background:#0d180c;border:1px solid #1e2e1c;border-radius:10px;padding:10px 14px;}
div[data-testid="stMetric"] label{color:#8aab80!important;}
div[data-testid="stMetricValue"]{color:#6fcf60!important;font-family:'Barlow Condensed',sans-serif;}
.sec{font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:700;
 letter-spacing:2px;text-transform:uppercase;color:#8aab80;
 border-left:4px solid #4a9e3f;padding-left:10px;margin:8px 0 12px;}
.pump-row-4{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:8px;}
@media (max-width:1100px){.pump-row-4{grid-template-columns:repeat(2,1fr);}}
.pump-stock{background:#111c10;border:1px solid #1e2e1c;border-radius:12px;padding:12px 10px;
 text-align:center;font-family:'Barlow Condensed',sans-serif;}
.pump-stock-title{font-size:10px;font-weight:700;color:#8aab80;text-transform:uppercase;
 letter-spacing:1px;margin-bottom:6px;line-height:1.25;}
.pump-stock-saldo{font-size:18px;font-weight:700;margin-top:4px;}
.pump-stock-cap{font-size:10px;color:#8aab80;margin-top:2px;}
.pump-stock-badge{display:inline-block;margin-top:6px;font-size:9px;font-weight:700;
 padding:2px 10px;border-radius:12px;text-transform:uppercase;}
.logo-frame{background:linear-gradient(145deg,#0a1628,#0d2040);border:2px solid #c9a227;
 border-radius:12px;padding:5px;display:inline-block;box-shadow:0 4px 18px rgba(0,0,0,.45);}
.logo-frame img{display:block;border-radius:8px;}
.sidebar-logo-wrap{margin-top:24px;padding-top:16px;border-top:1px solid #1e2e1c;}
</style>
""", unsafe_allow_html=True)


def fmt_l_tank(v):
    try:
        return f"{float(v):,.1f} L".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "0,0 L"


def fill_color(pct, accent):
    if pct <= 20:
        return "#e74c3c"
    if pct <= 40:
        return "#d4a017"
    return accent


def level_badge(pct, accent):
    if pct <= 20:
        return "NÍVEL CRÍTICO", "#e74c3c", "#2a1010"
    if pct <= 40:
        return "NÍVEL BAIXO", "#d4a017", "#2a2200"
    return "NÍVEL OK", accent, "#101820"


def fuel_pump_svg(pct, color, uid, width=72, height=98):
    pct = min(100.0, max(0.0, float(pct)))
    fz_top, fz_h = 82, 56
    fill_h = fz_h * pct / 100.0
    y_fill = fz_top + (fz_h - fill_h)
    pct_txt = f"{pct:.0f}%" if pct >= 10 else f"{pct:.1f}%"
    fs = 11 if width < 90 else 17
    return f"""<svg width="{width}" height="{height}" viewBox="0 0 110 150" xmlns="http://www.w3.org/2000/svg">
  <defs><clipPath id="pz{uid}"><rect x="27" y="{fz_top}" width="46" height="{fz_h}" rx="4"/></clipPath></defs>
  <rect x="12" y="138" width="86" height="7" rx="3.5" fill="#2c3440"/>
  <rect x="20" y="22" width="56" height="118" rx="9" fill="#4a5568" stroke="#1e2e1c" stroke-width="1.5"/>
  <rect x="28" y="30" width="40" height="20" rx="3" fill="#a8c0d8" opacity="0.45"/>
  <rect x="27" y="{y_fill:.2f}" width="46" height="{fill_h:.2f}" fill="{color}" clip-path="url(#pz{uid})"/>
  <rect x="70" y="55" width="18" height="12" rx="4" fill="#6a7585"/>
  <rect x="84" y="48" width="10" height="26" rx="5" fill="#8a95a5"/>
  <path d="M94 72 Q102 88 94 98" stroke="#1a1a1a" stroke-width="3" fill="none"/>
  <text x="52" y="108" text-anchor="middle" fill="#ffffff"
    font-family="Barlow Condensed,Arial,sans-serif" font-size="{fs}" font-weight="700">{pct_txt}</text>
</svg>"""


def pump_stock_card(pct, saldo, cap, title, accent, uid):
    color = fill_color(pct, accent)
    badge, badge_col, badge_bg = level_badge(pct, accent)
    svg = fuel_pump_svg(pct, color, f"s{uid}", 72, 98)
    return f"""
<div class="pump-stock">
  <div class="pump-stock-title">{title}</div>
  {svg}
  <div class="pump-stock-saldo" style="color:{accent}">{fmt_l_tank(saldo)}</div>
  <div class="pump-stock-cap">Tanque {fmt_l_tank(cap)}</div>
  <div class="pump-stock-badge" style="color:{badge_col};background:{badge_bg}">{badge}</div>
</div>"""

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
COMBUSTIVEIS_POSTO = ["DIESEL S-500 ADITIVADO", "DIESEL S-10", "GASOLINA COMUM", "ETANOL COMUM"]
TODOS_COMBUSTIVEIS = ["DIESEL S-500 ADITIVADO", "GASOLINA COMUM", "ETANOL COMUM", "DIESEL S-10"]

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
# CONSULTAS — estoque por tanque (4 combustíveis)
# ─────────────────────────────────────────────
def _query_row(sql, params=None):
    conn = get_conn()
    df = pd.read_sql_query(sql, conn, params=params or [])
    conn.close()
    return df.iloc[0].to_dict() if not df.empty else {}


def carregar_tabela_conciliacao_s500() -> pd.DataFrame:
    """Tabela entrada x saidas (desde ultima NF/transf.) ate hoje — S-500."""
    hoje = date.today()
    posto = _query_row(
        "SELECT data_carga, entrada_l, saida_posto_l, transferencia_comboio_l, saldo_litros "
        "FROM vw_saldo_posto_v2 LIMIT 1"
    )
    comboio = _query_row(
        "SELECT data_transferencia_anterior, data_transferencia, "
        "total_entrada_l, saida_comboio_v2_l, total_saida_l, saldo_litros "
        "FROM vw_saldo_comboio LIMIT 1"
    )
    rows = []
    if posto:
        ent = float(posto.get("entrada_l") or 0)
        cons = float(posto.get("saida_posto_l") or 0)
        trf = float(posto.get("transferencia_comboio_l") or 0)
        rows.append({
            "Local": "POSTO",
            "Combustivel": "DIESEL S-500 ADITIVADO",
            "Data Entrada": posto.get("data_carga"),
            "Entrada (L)": ent,
            "Abast/Consumo (L)": cons,
            "Transf. Comboio (L)": trf,
            "Total Saidas (L)": cons + trf,
            "Saldo (L)": float(posto.get("saldo_litros") or 0),
            "Ate": hoje,
        })
    if comboio:
        ent = float(comboio.get("total_entrada_l") or 0)
        abast = float(comboio.get("saida_comboio_v2_l") or 0)
        dt_ini = comboio.get("data_transferencia_anterior") or comboio.get("data_transferencia")
        rows.append({
            "Local": "COMBOIO",
            "Combustivel": "DIESEL S-500 ADITIVADO",
            "Data Entrada": dt_ini,
            "Entrada (L)": ent,
            "Abast/Consumo (L)": abast,
            "Transf. Comboio (L)": 0.0,
            "Total Saidas (L)": float(comboio.get("total_saida_l") or abast),
            "Saldo (L)": float(comboio.get("saldo_litros") or 0),
            "Ate": hoje,
        })
    df = pd.DataFrame(rows)
    if not df.empty and "Data Entrada" in df.columns:
        df["Data Entrada"] = pd.to_datetime(df["Data Entrada"]).dt.strftime("%d/%m/%Y")
        df["Ate"] = pd.to_datetime(df["Ate"]).dt.strftime("%d/%m/%Y")
    return df


def carregar_estoque_tanques():
    """4 tanques: comboio + posto S-500, S-10 e gasolina (views oficiais)."""
    cb = _query_row(
        "SELECT saldo_litros FROM vw_saldo_combustivel_geral "
        "WHERE upper(origem) = 'COMBOIO' LIMIT 1"
    )
    s500 = _query_row("SELECT saldo_litros FROM vw_saldo_posto_v2 LIMIT 1")
    s10 = _query_row("SELECT saldo_litros FROM vw_saldo_s10_posto LIMIT 1")
    gas = _query_row(
        "SELECT saldo_estimado AS saldo_litros FROM vw_saldo_gasolina_posto LIMIT 1"
    )
    return [
        {
            "titulo": "COMBOIO — DIESEL S-500",
            "saldo": float(cb.get("saldo_litros") or 0),
            "cap": CAP_COMBOIO,
            "accent": "#4a9e3f",
            "uid": "cb",
        },
        {
            "titulo": "POSTO — DIESEL S-500 ADITIVADO",
            "saldo": float(s500.get("saldo_litros") or 0),
            "cap": CAP_S500,
            "accent": "#3498db",
            "uid": "500",
        },
        {
            "titulo": "POSTO — DIESEL S-10",
            "saldo": float(s10.get("saldo_litros") or 0),
            "cap": CAP_S10,
            "accent": "#7ab0d4",
            "uid": "10",
        },
        {
            "titulo": "POSTO — GASOLINA COMUM",
            "saldo": float(gas.get("saldo_litros") or 0),
            "cap": CAP_GAS,
            "accent": "#e67e22",
            "uid": "gas",
        },
    ]


def carregar_saldo_geral():
    """Mantido para compatibilidade; preferir carregar_estoque_tanques()."""
    return pd.DataFrame(carregar_estoque_tanques())

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

def carregar_historico_posto(data_ini=None, data_fim=None):
    conn = get_conn()
    query = """SELECT data, veiculo AS frota, combustivel,
                      litros AS litros_consumidos, observacao
               FROM combustivel_historico_posto
               WHERE data >= %s"""
    params = [str(HIST_PLANILHA_INI)]
    if data_ini:
        query += " AND data >= %s"; params.append(str(data_ini))
    if data_fim:
        query += " AND data <= %s"; params.append(str(data_fim))
    else:
        query += " AND data <= %s"; params.append(str(HIST_PLANILHA_FIM))
    query += " ORDER BY data DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def carregar_consumo_posto_pwa(data_ini=None, data_fim=None, combustivel=None):
    """Saídas registradas pelo PWA do posto (tabela posto)."""
    conn = get_conn()
    query = """
        SELECT DATE(created_at) AS data, vehicle AS frota,
               fuel_type AS combustivel,
               COALESCE(operator, '') AS operador,
               liters AS litros_consumidos
        FROM posto
        WHERE DATE(created_at) >= %s
    """
    params = [str(PWA_POSTO_INI)]
    if data_ini:
        query += " AND DATE(created_at) >= %s"; params.append(str(data_ini))
    if data_fim:
        query += " AND DATE(created_at) <= %s"; params.append(str(data_fim))
    if combustivel and combustivel != "Todos":
        query += " AND fuel_type ILIKE %s"; params.append(f"%{combustivel}%")
    query += " ORDER BY created_at DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def carregar_consumo_posto_unificado(data_ini=None, data_fim=None, combustivel=None, origem=None):
    """Planilha (jan–14/mai/2026) + PWA (a partir de 18/mai/2026). Intervalo 15–17/mai sem dados."""
    frames = []
    if origem in (None, "Todos", "Planilha"):
        df_h = carregar_historico_posto(data_ini, data_fim)
        if not df_h.empty:
            df_h = df_h.copy()
            df_h["origem"] = "Planilha"
            df_h["detalhe"] = df_h["observacao"].fillna("")
            frames.append(df_h[["data", "frota", "combustivel", "litros_consumidos", "origem", "detalhe"]])
    if origem in (None, "Todos", "PWA"):
        df_p = carregar_consumo_posto_pwa(data_ini, data_fim, combustivel)
        if not df_p.empty:
            df_p = df_p.copy()
            df_p["origem"] = "PWA"
            df_p["detalhe"] = df_p["operador"].fillna("")
            frames.append(df_p[["data", "frota", "combustivel", "litros_consumidos", "origem", "detalhe"]])
    if not frames:
        return pd.DataFrame(columns=["data", "frota", "combustivel", "litros_consumidos", "origem", "detalhe"])
    df = pd.concat(frames, ignore_index=True)
    if combustivel and combustivel != "Todos":
        c = combustivel.upper()
        if "S-500" in c or "S500" in c:
            df = df[df["combustivel"].astype(str).str.upper().str.contains(r"S-?500|S500", regex=True, na=False)]
        elif "S-10" in c or "S10" in c:
            df = df[df["combustivel"].astype(str).str.upper().str.contains(r"S-?10|S10", regex=True, na=False)]
        elif "GASOLINA" in c:
            df = df[df["combustivel"].astype(str).str.upper().str.contains("GASOLINA", na=False)]
        elif "ETANOL" in c:
            df = df[df["combustivel"].astype(str).str.upper().str.contains("ETANOL", na=False)]
    return df.sort_values("data", ascending=False).reset_index(drop=True)


def carregar_consumo_posto(data_ini=None, data_fim=None, combustivel=None):
    """Compatível: agregado diário só do PWA (relatório de hoje)."""
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
        query += " AND fuel_type ILIKE %s"; params.append(f"%{combustivel}%")
    query += " GROUP BY DATE(created_at), vehicle, fuel_type, operator ORDER BY data DESC"
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
st.sidebar.title("Controle de Combustível")
pagina = st.sidebar.radio("Menu", [
    "📊 Saldo Geral",
    "⛽ Lançar Entrada",
    "🔄 Transferência",
    "🚛 Consumo Comboio",
    "🏪 Histórico Consumo Posto",
    "📋 Histórico Entradas",
    "📋 Histórico Transferências",
])
st.sidebar.markdown(
    f'<div class="sidebar-logo-wrap">{logo_html(96)}</div>',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════
# SALDO GERAL — relógio de estoque (4 tanques)
# ═══════════════════════════════════════════
if pagina == "📊 Saldo Geral":
    st.title("⛽ Controle de Combustível")
    st.markdown(
        '<div class="sec">Relógio de estoque — posto e comboio</div>',
        unsafe_allow_html=True,
    )

    tanques = carregar_estoque_tanques()
    cards = ""
    for t in tanques:
        pct = min(100.0, (t["saldo"] / t["cap"]) * 100) if t["cap"] > 0 else 0.0
        cards += pump_stock_card(pct, t["saldo"], t["cap"], t["titulo"], t["accent"], t["uid"])

    st.markdown(f'<div class="pump-row-4">{cards}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="sec">Conciliacao S-500 — entrada x saidas ate hoje</div>',
        unsafe_allow_html=True,
    )
    df_conc = carregar_tabela_conciliacao_s500()
    if df_conc.empty:
        st.warning("Sem dados de conciliacao S-500.")
    else:
        st.dataframe(
            df_conc,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Entrada (L)": st.column_config.NumberColumn(format="%.2f"),
                "Abast/Consumo (L)": st.column_config.NumberColumn(format="%.2f"),
                "Transf. Comboio (L)": st.column_config.NumberColumn(format="%.2f"),
                "Total Saidas (L)": st.column_config.NumberColumn(format="%.2f"),
                "Saldo (L)": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        st.caption(
            "POSTO: saldo = ultima NF − consumo PWA − transferencias ao comboio (desde a NF). "
            "COMBOIO: saldo = transferencias recebidas − abastecimentos comboio_v2 (desde a ultima carga)."
        )

    st.caption(
        f"Atualizado em: {date.today().strftime('%d/%m/%Y')} · SIGCF Bataguassu-MS"
    )
    st.caption(
        "Saídas do posto: menu **Histórico Consumo Posto** · "
        f"planilha {HIST_PLANILHA_INI.strftime('%d/%m/%Y')}–{HIST_PLANILHA_FIM.strftime('%d/%m/%Y')} · "
        f"PWA a partir de {PWA_POSTO_INI.strftime('%d/%m/%Y')} "
        "(intervalo 15–17/mai/2026 sem lançamentos — operação normal)."
    )

# ═══════════════════════════════════════════
# LANÇAR ENTRADA
# ═══════════════════════════════════════════
elif pagina == "⛽ Lançar Entrada":
    st.title("⛽ Lançar Entrada de Combustível")
    st.divider()

    # Destino e combustível FORA do form: widgets dentro de st.form não
    # disparam re-execução — a lista de combustíveis não atualizava ao trocar POSTO/COMBOIO.
    origem = st.selectbox("📍 Destino", ["POSTO", "COMBOIO"], key="lanc_entrada_destino")
    opcoes_combustivel = COMBUSTIVEIS_COMBOIO if origem == "COMBOIO" else COMBUSTIVEIS_POSTO
    combustivel = st.selectbox(
        "⛽ Combustível",
        opcoes_combustivel,
        key=f"lanc_entrada_comb_{origem}",
    )

    with st.form("form_entrada", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_ent = st.date_input("📅 Data", value=date.today())
            quantidade = st.number_input("💧 Quantidade (litros)", min_value=0.0, step=0.01, format="%.2f")
        with col2:
            valor_litro = st.number_input("💰 Valor por Litro (R$)", min_value=0.0, step=0.001, format="%.4f")
            fornecedor = st.text_input("🏢 Fornecedor")
            nota_fiscal = st.text_input("📄 Nota Fiscal")
        observacao = st.text_area("📝 Observação", height=68)
        submitted = st.form_submit_button("✅ Registrar Entrada", use_container_width=True, type="primary")

    if submitted:
        if quantidade <= 0:
            st.error("⚠️ Informe a quantidade de litros.")
        else:
            ok, msg = inserir_entrada({
                "data": str(data_ent),
                "combustivel": combustivel,
                "origem": origem,
                "quantidade_l": quantidade,
                "valor_litro": valor_litro,
                "fornecedor": fornecedor.strip().upper() or None,
                "nota_fiscal": nota_fiscal.strip() or None,
                "observacao": observacao.strip() or None,
            })
            if ok:
                st.success(
                    f"✅ {msg} | {combustivel} | {origem} | {fmt_l(quantidade)}"
                    + (f" | Total {fmt_r(quantidade * valor_litro)}" if valor_litro > 0 else "")
                )
                st.balloons()
            else:
                st.error(f"❌ {msg}")

# ═══════════════════════════════════════════
# TRANSFERÊNCIA
# ═══════════════════════════════════════════
elif pagina == "🔄 Transferência":
    st.title("🔄 Transferência de Combustível")
    st.divider()
    st.info("Movimentação entre POSTO e COMBOIO. O comboio opera somente DIESEL S-500 ADITIVADO.")

    # Origem fora do form pelo mesmo motivo da página de entrada.
    origem_t = st.selectbox("📤 Origem", ["POSTO", "COMBOIO"], key="lanc_transf_origem")
    destino_t = "COMBOIO" if origem_t == "POSTO" else "POSTO"
    st.markdown(f"**📥 Destino:** `{destino_t}`")

    with st.form("form_transf", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_t = st.date_input("📅 Data", value=date.today())
            # Toda transferência envolve o comboio, que só opera S-500.
            comb_t = st.selectbox("⛽ Combustível", COMBUSTIVEIS_COMBOIO, key="lanc_transf_comb")
        with col2:
            qtd_t = st.number_input("💧 Quantidade (litros)", min_value=0.0, step=0.01, format="%.2f")
        obs_t = st.text_area("📝 Observação", height=68)
        submitted = st.form_submit_button("✅ Registrar Transferência", use_container_width=True, type="primary")

    if submitted:
        if qtd_t <= 0:
            st.error("⚠️ Informe a quantidade de litros.")
        else:
            ok, msg = inserir_transferencia({
                "data": str(data_t),
                "combustivel": comb_t,
                "origem": origem_t,
                "destino": destino_t,
                "quantidade_l": qtd_t,
                "observacao": obs_t.strip() or None,
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
        with c2: f_fim = st.date_input("Data fim", value=None)

    df = carregar_consumo_comboio(f_ini, f_fim)
    if not df.empty:
        m1, m2 = st.columns(2)
        m1.metric("Total Litros", fmt_l(df["litros_consumidos"].sum()))
        m2.metric("Registros", len(df))

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
# HISTÓRICO CONSUMO POSTO (planilha + PWA)
# ═══════════════════════════════════════════
elif pagina == "🏪 Histórico Consumo Posto":
    st.title("🏪 Histórico de Consumo — Posto")
    st.divider()
    st.info(
        f"**Linha do tempo:** planilha importada "
        f"({HIST_PLANILHA_INI.strftime('%d/%m/%Y')} → {HIST_PLANILHA_FIM.strftime('%d/%m/%Y')}) · "
        f"PWA celular (a partir de {PWA_POSTO_INI.strftime('%d/%m/%Y')}). "
        "Dias **15 a 17/05/2026** sem registros (virada planilha → PWA)."
    )

    # ── RELATÓRIO DE HOJE (só PWA) ─────────
    with st.container(border=True):
        st.markdown("### 📤 Hoje — PWA posto")
        df_hoje = carregar_consumo_posto(date.today(), date.today())
        if df_hoje.empty:
            st.info("Nenhum abastecimento registrado hoje no PWA.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Diesel", fmt_l(df_hoje[df_hoje["combustivel"].str.contains("diesel", case=False, na=False)]["litros_consumidos"].sum()))
            c2.metric("Total Gasolina", fmt_l(df_hoje[df_hoje["combustivel"].str.contains("gasolina", case=False, na=False)]["litros_consumidos"].sum()))
            c3.metric("Frotas", df_hoje["frota"].nunique())
            st.dataframe(
                df_hoje.rename(columns={"data": "Data", "frota": "Frota",
                                        "combustivel": "Combustível",
                                        "litros_consumidos": "Litros"}),
                use_container_width=True, hide_index=True,
            )

    st.divider()

    # ── HISTÓRICO COMPLETO ─────────────────
    st.markdown("### 📜 Histórico completo (planilha + PWA)")
    with st.expander("🔍 Filtros", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            f_ini = st.date_input(
                "Data início", value=HIST_PLANILHA_INI,
                min_value=HIST_PLANILHA_INI,
            )
        with c2:
            f_fim = st.date_input("Data fim", value=date.today())
        with c3:
            f_comb = st.selectbox(
                "Combustível", ["Todos"] + TODOS_COMBUSTIVEIS, key="hist_posto_comb"
            )
        with c4:
            f_orig = st.selectbox(
                "Origem", ["Todos", "Planilha", "PWA"], key="hist_posto_origem"
            )

    df = carregar_consumo_posto_unificado(f_ini, f_fim, f_comb, f_orig)
    if df.empty:
        st.info("Nenhum registro no período selecionado.")
    else:
        n_plan = int((df["origem"] == "Planilha").sum())
        n_pwa = int((df["origem"] == "PWA").sum())
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total litros", fmt_l(df["litros_consumidos"].sum()))
        m2.metric("Registros", len(df))
        m3.metric("Planilha", n_plan)
        m4.metric("PWA", n_pwa)

        st.dataframe(
            df.rename(columns={
                "data": "Data", "frota": "Frota", "combustivel": "Combustível",
                "litros_consumidos": "Litros", "origem": "Origem", "detalhe": "Operador/Obs.",
            }),
            use_container_width=True, hide_index=True,
        )

        st.subheader("🏪 Consumo por frota (Top 15)")
        por_frota = (
            df.groupby("frota")["litros_consumidos"].sum()
            .reset_index().sort_values("litros_consumidos", ascending=False).head(15)
        )
        st.bar_chart(por_frota.set_index("frota"))

        st.subheader("📅 Litros por mês")
        df_mes = df.copy()
        df_mes["mes"] = pd.to_datetime(df_mes["data"]).dt.to_period("M").astype(str)
        por_mes = df_mes.groupby(["mes", "origem"])["litros_consumidos"].sum().reset_index()
        pivot_mes = por_mes.pivot(index="mes", columns="origem", values="litros_consumidos").fillna(0)
        st.bar_chart(pivot_mes)

        excel_per = gerar_excel(df.rename(columns={
            "data": "Data", "frota": "Frota", "combustivel": "Combustível",
            "litros_consumidos": "Litros (L)", "origem": "Origem", "detalhe": "Operador/Obs.",
        }))
        st.download_button(
            "⬇️ Exportar histórico — Excel",
            data=excel_per,
            file_name=f"historico_posto_{f_ini}_{f_fim}.xlsx",
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
        with c1: f_ini = st.date_input("Data início", value=None)
        with c2: f_fim = st.date_input("Data fim", value=None)
        with c3:
            f_comb = st.selectbox(
                "Combustível", ["Todos"] + TODOS_COMBUSTIVEIS, key="hist_entradas_comb"
            )
        with c4:
            f_orig = st.selectbox(
                "Origem", ["Todos", "COMBOIO", "POSTO"], key="hist_entradas_origem"
            )

    df = carregar_entradas(f_ini, f_fim,
                           f_comb if f_comb != "Todos" else None,
                           f_orig if f_orig != "Todos" else None)
    if df.empty:
        st.info("Nenhuma entrada encontrada.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Entradas", len(df))
        m2.metric("Total Litros", fmt_l(df["quantidade_l"].sum()))
        m3.metric("Valor Total", fmt_r(df["valor_total"].sum()))

        df_show = df.copy()
        df_show["quantidade_l"] = df_show["quantidade_l"].apply(fmt_l)
        df_show["valor_litro"] = df_show["valor_litro"].apply(lambda v: f"R$ {v:.4f}")
        df_show["valor_total"] = df_show["valor_total"].apply(fmt_r)
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
        sel = st.selectbox("Selecione o ID", ids, key="hist_entradas_del_id")
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
        with c2: f_fim = st.date_input("Data fim", value=None)

    df = carregar_transferencias(f_ini, f_fim)
    if df.empty:
        st.info("Nenhuma transferência encontrada.")
    else:
        m1, m2 = st.columns(2)
        m1.metric("Total Transferências", len(df))
        m2.metric("Total Litros", fmt_l(df["quantidade_l"].sum()))

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
        sel = st.selectbox("Selecione o ID", ids, key="hist_transf_del_id")
        reg = df[df["id"] == sel].iloc[0]
        st.caption(f"Data: {reg['data']} | {reg['combustivel']} | {reg['origem']} → {reg['destino']} | {fmt_l(reg['quantidade_l'])}")
        if st.button("🗑️ Confirmar Exclusão", type="primary"):
            deletar_transferencia(sel)
            st.success("Transferência excluída.")
            st.rerun()
