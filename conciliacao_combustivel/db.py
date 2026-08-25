"""Conexão Supabase (PostgreSQL) para conciliação combustível."""
from __future__ import annotations

import tomllib
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[2]
SECRETS = ROOT / "requisicao-compras" / ".streamlit" / "secrets.toml"


def load_cfg() -> dict:
    with open(SECRETS, "rb") as f:
        return tomllib.load(f)["connections"]["supabase"]


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
