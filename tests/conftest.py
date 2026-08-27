"""Aísla cada test: la Fase 8 reveló que los tests de fases anteriores (Fase 6/7) dejaban
mensajes reales en 'general', rompiendo los conteos exactos que otros tests asumían sobre el
seed. En vez de mockear la base (prohibido — se prueba contra PostgreSQL real), se resetea el
contenido a un estado idéntico al seed antes de cada test, usando el rol admin (bypassa RLS).
"""

import os
from pathlib import Path

import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SEED_FILE = REPO_ROOT / "database" / "seeds" / "0001_demo.sql"

TABLES = (
    "rw_message_embeddings",
    "rw_message_history",
    "rw_messages",
    "rw_channel_members",
    "rw_channels",
    "rw_refresh_tokens",
    "rw_users",
)


@pytest.fixture(autouse=True)
def _reset_database_to_seed():
    admin_dsn = os.environ["DATABASE_URL"]
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(f"TRUNCATE {', '.join(TABLES)} CASCADE;")
            cur.execute(SEED_FILE.read_text(encoding="utf-8"))
    yield
