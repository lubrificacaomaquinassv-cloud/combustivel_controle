"""Conexão Supabase (PostgreSQL) para conciliação combustível."""
from __future__ import annotations

import tomllib
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

# secrets.toml local (scripts / dev) — vários layouts de pasta
_SECRETS_CANDIDATES = (
    Path(__file__).resolve().parents[2] / "requisicao-compras" / ".streamlit" / "secrets.toml",
    Path(__file__).resolve().parents[1].parent / "requisicao-compras" / ".streamlit" / "secrets.toml",
)


def load_cfg() -> dict:
    """Streamlit Cloud usa st.secrets['db']; local usa secrets.toml."""
    try:
        import streamlit as st

        if "db" in st.secrets:
            s = st.secrets["db"]
            return {
                "host": s["host"],
                "port": s["port"],
                "database": s["dbname"],
                "username": s["user"],
                "password": s["password"],
            }
    except Exception:
        pass

    for path in _SECRETS_CANDIDATES:
        if path.is_file():
            with open(path, "rb") as f:
                return tomllib.load(f)["connections"]["supabase"]

    raise FileNotFoundError(
        "Credenciais do banco não encontradas. "
        "Configure st.secrets['db'] no Streamlit Cloud ou secrets.toml local."
    )


def connect():
    cfg = load_cfg()
    return psycopg2.connect(
        host=cfg["host"],
        port=cfg["port"],
        database=cfg["database"],
        user=cfg["username"],
        password=cfg["password"],
        sslmode="require",
    )


def query_all(sql: str, params=None) -> list[dict]:
    conn = connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(sql, params or [])
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def query_one(sql: str, params=None) -> dict | None:
    rows = query_all(sql, params)
    return rows[0] if rows else None
