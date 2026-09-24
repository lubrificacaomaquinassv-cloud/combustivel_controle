import streamlit as st
import psycopg2
from sigcf_auth import exigir_acesso, logo_html
import pandas as pd
from datetime import date
from io import BytesIO

from conciliacao_combustivel.api import (
    executar_auditoria_completa,
    resumo_conciliacao_s500,
    resumo_sap_baixas,
    resumo_tanques,
)
from regua_tanque import litros_da_regua, tabela_regua
from regua_tabelas import (
    COMBOIO_ALTURA_CHEIA_CM,
    COMBOIO_CAPACIDADE_L,
    litros_comboio,
    litros_posto_s500,
)

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

CAP_COMBOIO = 6000
CAP_S500 = 30000
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
def obter_saldo_remanescente_comboio() -> float:
    """Saldo no comboio imediatamente antes de nova carga POSTO->COMBOIO."""
    row = _query_row("SELECT saldo_litros FROM vw_saldo_comboio LIMIT 1")
    return float(row.get("saldo_litros") or 0)


def obter_saldo_remanescente_posto(combustivel: str) -> float:
    """Saldo no tanque imediatamente antes de registrar nova NF."""
    if "S-500" in (combustivel or ""):
        row = _query_row("SELECT saldo_litros FROM vw_saldo_posto_v2 LIMIT 1")
    elif "S-10" in (combustivel or ""):
        row = _query_row("SELECT saldo_litros FROM vw_saldo_s10_posto LIMIT 1")
    elif "GASOLINA" in (combustivel or ""):
        row = _query_row("SELECT saldo_estimado AS saldo_litros FROM vw_saldo_gasolina_posto LIMIT 1")
    else:
        return 0.0
    return float(row.get("saldo_litros") or 0)


def inserir_entrada(row: dict):
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO combustivel_entrada
                (data, combustivel, origem, quantidade_l, valor_litro,
                 fornecedor, nota_fiscal, observacao, saldo_remanescente_l)
            VALUES (%(data)s, %(combustivel)s, %(origem)s, %(quantidade_l)s,
                    %(valor_litro)s, %(fornecedor)s, %(nota_fiscal)s, %(observacao)s,
                    %(saldo_remanescente_l)s)
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
                (data, combustivel, origem, destino, quantidade_l, observacao,
                 saldo_remanescente_l)
            VALUES (%(data)s, %(combustivel)s, %(origem)s, %(destino)s,
                    %(quantidade_l)s, %(observacao)s, %(saldo_remanescente_l)s)
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
        "SELECT data_carga, entrada_l, saldo_remanescente_l, entrada_efetiva_l, "
        "saida_posto_l, transferencia_comboio_l, saldo_litros "
        "FROM vw_saldo_posto_v2 LIMIT 1"
    )
    comboio = _query_row(
        "SELECT data_transferencia, total_entrada_l, saldo_ciclo_anterior_l, "
        "entrada_efetiva_l, saida_comboio_v2_l, devolucao_posto_l, total_saida_l, "
        "saldo_litros FROM vw_saldo_comboio LIMIT 1"
    )
    rows = []
    if posto:
        ent_nf = float(posto.get("entrada_l") or 0)
        rem = float(posto.get("saldo_remanescente_l") or 0)
        ent = float(posto.get("entrada_efetiva_l") or ent_nf + rem)
        cons = float(posto.get("saida_posto_l") or 0)
        trf = float(posto.get("transferencia_comboio_l") or 0)
        rows.append({
            "Local": "POSTO",
            "Combustivel": "DIESEL S-500 ADITIVADO",
            "Data Entrada": posto.get("data_carga"),
            "NF (L)": ent_nf,
            "Remanescente (L)": rem,
            "Entrada efetiva (L)": ent,
            "Abast/Consumo (L)": cons,
            "Transf. Comboio (L)": trf,
            "Retorno POSTO (L)": 0.0,
            "Total Saidas (L)": cons + trf,
            "Saldo (L)": float(posto.get("saldo_litros") or 0),
            "Ate": hoje,
        })
    if comboio:
        ent_trf = float(comboio.get("total_entrada_l") or 0)
        rem = float(comboio.get("saldo_ciclo_anterior_l") or 0)
        ent = float(comboio.get("entrada_efetiva_l") or ent_trf + rem)
        abast = float(comboio.get("saida_comboio_v2_l") or 0)
        ret_posto = float(comboio.get("devolucao_posto_l") or 0)
        dt_ini = comboio.get("data_transferencia")
        rows.append({
            "Local": "COMBOIO",
            "Combustivel": "DIESEL S-500 ADITIVADO",
            "Data Entrada": dt_ini,
            "Carga (L)": ent_trf,
            "Remanescente (L)": rem,
            "Entrada efetiva (L)": ent,
            "Abast/Consumo (L)": abast,
            "Transf. Comboio (L)": 0.0,
            "Retorno POSTO (L)": ret_posto,
            "Total Saidas (L)": float(comboio.get("total_saida_l") or (abast + ret_posto)),
            "Saldo (L)": float(comboio.get("saldo_litros") or 0),
            "Ate": hoje,
        })
    df = pd.DataFrame(rows)
    if not df.empty and "Data Entrada" in df.columns:
        df["Data Entrada"] = pd.to_datetime(df["Data Entrada"]).dt.strftime("%d/%m/%Y")
        df["Ate"] = pd.to_datetime(df["Ate"]).dt.strftime("%d/%m/%Y")
    return df


def carregar_movimentos_comboio_s500(dias: int = 14) -> pd.DataFrame:
    """Transferências S-500 que envolvem o comboio (cargas, zeramentos, ajustes)."""
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT id, data, origem, destino, quantidade_l,
               coalesce(saldo_remanescente_l, 0) AS saldo_remanescente_l,
               CASE WHEN upper(origem) = 'POSTO' AND upper(destino) = 'COMBOIO'
                    THEN quantidade_l + coalesce(saldo_remanescente_l, 0)
                    ELSE quantidade_l END AS entrada_efetiva_l,
               observacao, created_at
        FROM combustivel_transferencia
        WHERE combustivel ILIKE '%%S-500%%'
          AND (upper(origem) = 'COMBOIO' OR upper(destino) = 'COMBOIO')
          AND data >= current_date - %s
        ORDER BY data DESC, created_at DESC, id DESC
        """,
        conn,
        params=[dias],
    )
    conn.close()
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


def movimento_comboio_dia(dia):
    """Entrada (posto→comboio) e saídas comboio_v2 no dia (fuso MS)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT coalesce(sum(quantidade_l), 0)
        FROM combustivel_transferencia
        WHERE upper(coalesce(origem, '')) = 'POSTO'
          AND upper(coalesce(destino, '')) = 'COMBOIO'
          AND data = %s
        """,
        [dia],
    )
    entrada = float(cur.fetchone()[0] or 0)
    cur.execute(
        """
        SELECT coalesce(sum(liters), 0)
        FROM comboio_v2
        WHERE (created_at AT TIME ZONE 'America/Campo_Grande')::date = %s
        """,
        [dia],
    )
    saida = float(cur.fetchone()[0] or 0)
    cur.execute(
        "SELECT saldo_litros FROM vw_saldo_comboio LIMIT 1"
    )
    row = cur.fetchone()
    saldo_view = float(row[0] or 0) if row else 0.0
    cur.close()
    conn.close()
    return entrada, saida, saldo_view


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
    "🔍 Conciliação / Auditoria",
    "⛽ Lançar Entrada",
    "🔄 Transferência",
    "🚛 Consumo Comboio",
    "📏 Régua Comboio",
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
        pct = min(100.0, max(0.0, (t["saldo"] / t["cap"]) * 100)) if t["cap"] > 0 else 0.0
        saldo_card = max(0.0, min(float(t["cap"]), float(t["saldo"])))
        cards += pump_stock_card(pct, saldo_card, t["cap"], t["titulo"], t["accent"], t["uid"])

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
                "Retorno POSTO (L)": st.column_config.NumberColumn(format="%.2f"),
                "Total Saidas (L)": st.column_config.NumberColumn(format="%.2f"),
                "Saldo (L)": st.column_config.NumberColumn(format="%.2f"),
            },
        )
        st.caption(
            "POSTO: saldo = NF + remanescente − consumo − transf. comboio. "
            "COMBOIO: saldo = remanescente tanque + carga − abast. apos a carga. "
            "Teto comboio 5.000 L."
        )

    st.markdown(
        '<div class="sec">Movimentos comboio — cargas e zeramentos (S-500)</div>',
        unsafe_allow_html=True,
    )
    df_mov = carregar_movimentos_comboio_s500(14)
    if df_mov.empty:
        st.info("Nenhuma transferencia envolvendo comboio nos ultimos 14 dias.")
    else:
        df_mov_show = df_mov.copy()
        for col in ("quantidade_l", "saldo_remanescente_l", "entrada_efetiva_l"):
            if col in df_mov_show.columns:
                df_mov_show[col] = df_mov_show[col].apply(lambda x: fmt_l(float(x or 0)))
        df_mov_show = df_mov_show.rename(columns={
            "id": "ID", "data": "Data", "origem": "Origem", "destino": "Destino",
            "quantidade_l": "Carga (L)", "saldo_remanescente_l": "Remanescente (L)",
            "entrada_efetiva_l": "Efetiva tanque (L)", "observacao": "Observacao",
        })
        cols = ["ID", "Data", "Origem", "Destino", "Carga (L)", "Remanescente (L)",
                "Efetiva tanque (L)", "Observacao"]
        cols = [c for c in cols if c in df_mov_show.columns]
        st.dataframe(df_mov_show[cols], use_container_width=True, hide_index=True)
        st.caption(
            "Ciclo: 3.019 (zero) − 1.017 − 811 = 1.191 | +3.673 = 4.864 | +802,40 = 5.666,40 | "
            "−1.022 (apos carga 802) = **4.644,40 L** saldo."
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
# CONCILIAÇÃO / AUDITORIA (Python vs Supabase)
# ═══════════════════════════════════════════
elif pagina == "🔍 Conciliação / Auditoria":
    st.title("🔍 Conciliação e Auditoria")
    st.markdown(
        '<div class="sec">Validação Python — entradas, saídas, transferências e baixas SAP</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Recalcula saldos a partir das tabelas brutas (posto, comboio_v2, "
        "combustivel_entrada, combustivel_transferencia) e compara com as views oficiais."
    )

    if st.button("▶ Executar auditoria completa", type="primary"):
        st.session_state["auditoria_comb"] = executar_auditoria_completa()

    aud = st.session_state.get("auditoria_comb")
    if not aud:
        st.info("Clique em **Executar auditoria completa** para validar o estoque.")
    else:
        if aud["ok_geral"]:
            st.success("Conciliação OK — saldos Python batem com as views Supabase.")
        else:
            st.error("Divergências encontradas — revise os alertas abaixo.")

        st.caption(f"Gerado em: {aud['gerado_em']}")

        st.markdown("#### Conciliação S-500 (POSTO + COMBOIO)")
        df_conc = resumo_conciliacao_s500()
        st.dataframe(
            df_conc,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Entrada (L)": st.column_config.NumberColumn(format="%.2f"),
                "Consumo (L)": st.column_config.NumberColumn(format="%.2f"),
                "Transf. (L)": st.column_config.NumberColumn(format="%.2f"),
                "Saldo calc. (L)": st.column_config.NumberColumn(format="%.2f"),
                "Saldo view (L)": st.column_config.NumberColumn(format="%.2f"),
                "Dif. (L)": st.column_config.NumberColumn(format="%.3f"),
            },
        )

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Tanques (views oficiais)")
            st.dataframe(resumo_tanques(), use_container_width=True, hide_index=True)
        with c2:
            st.markdown("#### Baixas SAP")
            st.dataframe(resumo_sap_baixas(), use_container_width=True, hide_index=True)

        if aud["alertas"]:
            st.markdown("#### Alertas")
            for al in aud["alertas"]:
                st.warning(al)

        with st.expander("Últimas entradas (combustivel_entrada)"):
            st.dataframe(pd.DataFrame(aud["entradas"]), use_container_width=True, hide_index=True)

        with st.expander("Últimas transferências (combustivel_transferencia)"):
            st.dataframe(pd.DataFrame(aud["transferencias"]), use_container_width=True, hide_index=True)

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

    saldo_rem_atual = 0.0
    if origem == "POSTO":
        saldo_rem_atual = obter_saldo_remanescente_posto(combustivel)
        st.info(
            f"Saldo remanescente no tanque **antes** desta NF: **{fmt_l(saldo_rem_atual)}**. "
            f"Será somado à quantidade da nota fiscal."
        )

    with st.form("form_entrada", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_ent = st.date_input("📅 Data", value=date.today())
            quantidade = st.number_input("💧 Quantidade NF (litros)", min_value=0.0, step=0.01, format="%.2f")
        with col2:
            valor_litro = st.number_input("💰 Valor por Litro (R$)", min_value=0.0, step=0.001, format="%.4f")
            fornecedor = st.text_input("🏢 Fornecedor")
            nota_fiscal = st.text_input("📄 Nota Fiscal")
        remanescente = 0.0
        if origem == "POSTO":
            remanescente = st.number_input(
                "Remanescente no tanque (L) — somado à NF",
                value=float(saldo_rem_atual),
                step=0.01,
                format="%.2f",
                help="Medição ou saldo do sistema imediatamente antes do descarregamento.",
            )
            st.caption(
                f"Entrada efetiva no tanque: **{fmt_l(quantidade + remanescente)}** "
                f"(NF {fmt_l(quantidade)} + remanescente {fmt_l(remanescente)})"
            )
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
                "saldo_remanescente_l": remanescente if origem == "POSTO" else None,
            })
            if ok:
                total_tanque = quantidade + (remanescente if origem == "POSTO" else 0.0)
                st.success(
                    f"✅ {msg} | {combustivel} | {origem} | NF {fmt_l(quantidade)}"
                    + (f" + rem. {fmt_l(remanescente)}" if origem == "POSTO" else "")
                    + f" = {fmt_l(total_tanque)} no tanque"
                    + (f" | Total R$ {fmt_r(quantidade * valor_litro)}" if valor_litro > 0 else "")
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
    st.info(
        "Movimentação entre POSTO e COMBOIO. O comboio opera somente DIESEL S-500 ADITIVADO. "
        "Na carga POSTO→COMBOIO, informe os **cm da régua** antes e depois do abastecimento."
    )

    origem_t = st.selectbox("📤 Origem", ["POSTO", "COMBOIO"], key="lanc_transf_origem")
    destino_t = "COMBOIO" if origem_t == "POSTO" else "POSTO"
    st.markdown(f"**📥 Destino:** `{destino_t}`")

    saldo_rem_sistema = 0.0
    cm_antes = 0.0
    cm_depois = 0.0
    cm_posto_antes = 0.0
    litros_antes = 0.0
    litros_depois = 0.0
    litros_posto_antes = 0.0
    diff_bomba = 0.0

    if origem_t == "POSTO":
        saldo_rem_sistema = obter_saldo_remanescente_comboio()
        st.caption(f"Saldo calculado pelo sistema (referência): **{fmt_l(saldo_rem_sistema)}**")

        st.markdown('<div class="sec">Medição régua — comboio</div>', unsafe_allow_html=True)
        r1, r2 = st.columns(2)
        with r1:
            cm_antes = st.number_input(
                "📏 Régua ANTES — comboio (cm)",
                min_value=0.0,
                max_value=COMBOIO_ALTURA_CHEIA_CM,
                step=0.5,
                format="%.1f",
                key="transf_cm_antes_comboio",
                help="Medir com comboio nivelado antes de receber diesel.",
            )
        with r2:
            cm_depois = st.number_input(
                "📏 Régua DEPOIS — comboio (cm)",
                min_value=0.0,
                max_value=COMBOIO_ALTURA_CHEIA_CM,
                step=0.5,
                format="%.1f",
                key="transf_cm_depois_comboio",
                help="Medir após abastecer (ex.: 77 cm → 3.280 L).",
            )

        litros_antes = litros_comboio(cm_antes) if cm_antes > 0 else 0.0
        litros_depois = litros_comboio(cm_depois) if cm_depois > 0 else 0.0

        m1, m2, m3 = st.columns(3)
        m1.metric("Volume régua ANTES", fmt_l(litros_antes))
        m2.metric("Volume régua DEPOIS", fmt_l(litros_depois))
        if litros_depois > 0 and litros_antes > 0:
            m3.metric("Variação régua", fmt_l(litros_depois - litros_antes))

        st.markdown('<div class="sec">Medição régua — posto (opcional)</div>', unsafe_allow_html=True)
        cm_posto_antes = st.number_input(
            "📏 Régua posto S-500 antes da transferência (cm)",
            min_value=0.0,
            step=0.5,
            format="%.1f",
            key="transf_cm_antes_posto",
        )
        if cm_posto_antes > 0:
            litros_posto_antes = litros_posto_s500(cm_posto_antes)
            st.caption(f"Volume posto (tabela S-500): **{fmt_l(litros_posto_antes)}**")

    with st.form("form_transf", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_t = st.date_input("📅 Data", value=date.today())
            comb_t = st.selectbox("⛽ Combustível", COMBUSTIVEIS_COMBOIO, key="lanc_transf_comb")
        with col2:
            qtd_t = st.number_input(
                "💧 Carga bomba / transferência (litros)",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                help="Litros registrados na bomba ou contador da transferência.",
            )

        rem_comboio = 0.0
        if origem_t == "POSTO":
            rem_default = litros_antes if cm_antes > 0 else 0.0
            rem_comboio = st.number_input(
                "Remanescente comboio (L) — somado à carga",
                value=rem_default,
                step=0.01,
                format="%.2f",
                help=(
                    "Use o volume da régua ANTES. Se a régua antes zerou mas a conferência "
                    "pós-carga indicar diferença, lance a diferença aqui (ex.: 266 L)."
                ),
            )

            if qtd_t > 0 and litros_depois > 0:
                esperado = rem_comboio + qtd_t
                diff_bomba = litros_depois - esperado
                st.caption(
                    f"Conferência: régua depois **{fmt_l(litros_depois)}** | "
                    f"rem + bomba **{fmt_l(esperado)}** | diferença **{fmt_l(diff_bomba)}**"
                )
                if litros_antes <= 0 and abs(diff_bomba) > 0.01:
                    st.warning(
                        f"Diferença bomba vs régua pós-carga: **{fmt_l(diff_bomba)}**. "
                        f"Você pode lançar **{fmt_l(max(diff_bomba, 0))}** como remanescente "
                        f"para fechar com a régua depois ({fmt_l(litros_depois)} L)."
                    )

            st.caption(
                f"Entrada efetiva no comboio: **{fmt_l(qtd_t + rem_comboio)}** "
                f"(carga {fmt_l(qtd_t)} + remanescente {fmt_l(rem_comboio)})"
            )

        obs_t = st.text_area("📝 Observação", height=68)
        submitted = st.form_submit_button("✅ Registrar Transferência", use_container_width=True, type="primary")

    if submitted:
        if qtd_t <= 0:
            st.error("⚠️ Informe a quantidade de litros.")
        else:
            obs_parts = []
            if obs_t.strip():
                obs_parts.append(obs_t.strip())
            if origem_t == "POSTO":
                if cm_antes > 0 or litros_antes > 0:
                    obs_parts.append(
                        f"Régua comboio antes: {cm_antes:.1f} cm = {litros_antes:.1f} L"
                    )
                if cm_depois > 0 or litros_depois > 0:
                    obs_parts.append(
                        f"Régua comboio depois: {cm_depois:.1f} cm = {litros_depois:.1f} L"
                    )
                if cm_posto_antes > 0:
                    obs_parts.append(
                        f"Régua posto antes: {cm_posto_antes:.1f} cm = {litros_posto_antes:.1f} L"
                    )
                if qtd_t > 0 and litros_depois > 0:
                    obs_parts.append(
                        f"Conferência bomba: carga {qtd_t:.1f} L | diff régua {diff_bomba:+.1f} L"
                    )

            ok, msg = inserir_transferencia({
                "data": str(data_t),
                "combustivel": comb_t,
                "origem": origem_t,
                "destino": destino_t,
                "quantidade_l": qtd_t,
                "observacao": " | ".join(obs_parts) if obs_parts else None,
                "saldo_remanescente_l": rem_comboio if origem_t == "POSTO" else None,
            })
            if ok:
                total_cb = qtd_t + (rem_comboio if origem_t == "POSTO" else 0.0)
                st.success(
                    f"✅ {msg} | {fmt_l(qtd_t)} de {origem_t} → {destino_t}"
                    + (f" = {fmt_l(total_cb)} no comboio" if origem_t == "POSTO" else "")
                )
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
# RÉGUA DO COMBOIO
# ═══════════════════════════════════════════
elif pagina == "📏 Régua Comboio":
    st.title("Régua do comboio")
    st.caption(
        "Cálculo simples: saldo anterior + entrada − saídas do dia = teórico. "
        "A régua (cm molhados) vira litros pelo cilindro deitado — perto do tanque real."
    )

    with st.expander("Ajustar tanque (uma vez)", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            cap_r = st.number_input("Capacidade (L)", min_value=100, value=CAP_COMBOIO, step=50)
        with c2:
            alt_r = st.number_input(
                "Régua no cheio (cm)",
                min_value=10.0,
                value=150.0,
                step=0.5,
                help="Altura molhada com o tanque cheio. Meça uma vez.",
            )
        with c3:
            passo_r = st.selectbox("Passo da tabela (cm)", [1, 2, 5], index=1)
        pts_txt = st.text_area(
            "Pontos da tabela da régua (opcional) — um por linha: cm, litros",
            placeholder="0, 0\n20, 480\n75, 2500\n150, 5000",
        )
        pontos_r = []
        for ln in pts_txt.splitlines():
            bits = ln.replace(";", ",").split(",")
            if len(bits) >= 2:
                try:
                    pontos_r.append((float(bits[0].strip()), float(bits[1].strip())))
                except ValueError:
                    pass

    dia_r = st.date_input("Data da medição", value=date.today())
    try:
        ent_auto, sai_auto, saldo_view = movimento_comboio_dia(dia_r)
    except Exception as e:
        ent_auto, sai_auto, saldo_view = 0.0, 0.0, 0.0
        st.warning(f"Não foi possível ler o movimento do PWA: {e}")

    if st.session_state.get("regua_dia") != str(dia_r):
        st.session_state.regua_dia = str(dia_r)
        st.session_state.regua_ent = float(ent_auto)
        st.session_state.regua_sai = float(sai_auto)

    c1, c2 = st.columns(2)
    with c1:
        ant_r = st.number_input(
            "Saldo anterior (L)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            help="Volume do último dia (anotado ou régua). No primeiro uso, informe o que tinha no tanque.",
        )
        ent_r = st.number_input("Entrada (L)", min_value=0.0, step=1.0, key="regua_ent")
        sai_r = st.number_input("Saídas do dia (L)", min_value=0.0, step=1.0, key="regua_sai")
    with c2:
        cm_r = st.number_input("Régua — cm molhados", min_value=0.0, value=0.0, step=0.5)
        vol_regua = litros_da_regua(cm_r, alt_r, cap_r, pontos_r or None) if cm_r > 0 else 0.0
        anot_r = st.number_input(
            "Volume anotado (L)",
            min_value=0.0,
            value=0.0,
            step=1.0,
            help="Deixe 0 para usar o volume da régua. Preencha se for confirmar um valor diferente.",
        )
        obs_r = st.text_input("Anotação", placeholder="Ex.: medido parado, tanque nivelado")

    teorico_r = ant_r + ent_r - sai_r
    vol_final = anot_r if anot_r > 0 else vol_regua
    diff_r = (vol_final - teorico_r) if (cm_r > 0 or anot_r > 0) else None

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Teórico hoje", fmt_l(teorico_r))
    m2.metric("Régua (calculado)", fmt_l(vol_regua) if cm_r > 0 else "—")
    m3.metric("Volume anotado", fmt_l(vol_final) if vol_final else "—")
    m4.metric(
        "Diferença (anotado − teórico)",
        fmt_l(diff_r) if diff_r is not None else "—",
        delta=f"{diff_r:+.0f} L vs livro" if diff_r is not None else None,
    )
    st.caption(
        f"Teórico = {fmt_l(ant_r)} + {fmt_l(ent_r)} − {fmt_l(sai_r)}. "
        f"Saldo da view do sistema agora: {fmt_l(saldo_view)}. "
        "Entrada e saídas já vêm do PWA do dia; ajuste se a régua foi lida antes de algum abastecimento."
    )

    tab_df = pd.DataFrame(
        tabela_regua(alt_r, cap_r, float(passo_r), pontos_r or None),
        columns=["Régua (cm)", "Volume (L)"],
    )
    tab_df["% tanque"] = (tab_df["Volume (L)"] / cap_r * 100).round(1)
    st.markdown("##### Tabela da régua (imprimir / colar no tanque)")
    st.dataframe(tab_df, use_container_width=True, hide_index=True, height=280)
    st.download_button(
        "Baixar tabela da régua (Excel)",
        data=gerar_excel(tab_df),
        file_name=f"tabela_regua_comboio_{int(alt_r)}cm.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    if obs_r:
        st.info(f"Anotação: {obs_r}")
    st.caption(
        "No pátio, sem internet: abra o arquivo `regua_comboio.html` no celular "
        "(pasta ATUALIZACAO_S10). Os lançamentos ficam no aparelho."
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
