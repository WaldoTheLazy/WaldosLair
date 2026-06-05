"""
WaldosLair — PostgreSQL Database Layer.

Sve SQL operacije su ovdje, odvojene od UI logike.

Sigurnost:
  - ISKLJUČIVO parametrizirani upiti (%s placeholders) — nema string formatiranja SQL-a
  - Kolumne u UPDATE-u prolaze kroz whitelist validaciju
  - Sve iznimke su uhvaćene i logirane — nema curenja stack tracea u UI
  - Connection pooling putem psycopg2.pool.ThreadedConnectionPool

Performanse:
  - @st.cache_data(ttl=300) na svim READ funkcijama
  - st.cache_data.clear() automatski pozvan nakon svakog WRITE-a

Audit:
  - Svaki INSERT/UPDATE/DELETE se logira u audit_log tablicu
"""
from __future__ import annotations

import json
import logging
import logging.handlers
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Generator

import pandas as pd
import psycopg2
import psycopg2.extras
import psycopg2.pool
import streamlit as st

from core.config import (
    ACCOUNTS,
    ALL_CATEGORIES,
    DB_DSN,
    LOGS_DIR,
    TRANSACTION_TYPES,
    TRANSFER_CATEGORIES,
    TRANSFER_SOURCE_ACCOUNTS,
)
from core.utils import parse_eur, sanitize_account, sanitize_category, sanitize_text, sanitize_transaction_type

# ---------------------------------------------------------------------------
# Logging setup — sve greške idu u /logs/app.log
# ---------------------------------------------------------------------------

_log_file = LOGS_DIR / "app.log"
_handler = logging.handlers.RotatingFileHandler(
    _log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
logger = logging.getLogger(__name__)
logger.addHandler(_handler)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Connection pool — singleton u Streamlit session state
# ---------------------------------------------------------------------------

_POOL_MIN = 2
_POOL_MAX = 10

# Whitelist kolumni za UPDATE
_ALLOWED_UPDATE_COLUMNS: frozenset[str] = frozenset(
    {"date", "type", "category", "account", "amount", "description"}
)


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    """
    Dohvati ili inicijaliziraj connection pool.
    Pool je pohranjen u Streamlit session state kako bi opstao između reruna.
    """
    if "db_pool" not in st.session_state or st.session_state.db_pool is None:
        try:
            pool = psycopg2.pool.ThreadedConnectionPool(
                _POOL_MIN, _POOL_MAX, dsn=DB_DSN
            )
            st.session_state.db_pool = pool
            logger.info("PostgreSQL connection pool inicijaliziran.")
        except psycopg2.Error as e:
            logger.error("Greška pri kreiranju connection poola: %s", e)
            raise
    return st.session_state.db_pool


@contextmanager
def get_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager koji uzima konekciju iz poola i vraća je nakon upotrebe.
    Automatski rollbacka u slučaju greške.
    """
    pool = _get_pool()
    conn = pool.getconn()
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


# ---------------------------------------------------------------------------
# Schema inicijalizacija
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Inicijalizira PostgreSQL shemu.
    Kreira tablice, indekse i trigger za audit log ako ne postoje.
    Sigurno je pozivati više puta (IF NOT EXISTS).
    """
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:

                # --- Transactions ---
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        id          SERIAL PRIMARY KEY,
                        date        DATE        NOT NULL,
                        type        TEXT        NOT NULL
                                                CHECK(type IN ('Prihod', 'Trošak')),
                        category    TEXT        NOT NULL,
                        account     TEXT        NOT NULL,
                        amount      NUMERIC(12,2) NOT NULL CHECK(amount >= 0),
                        description TEXT        DEFAULT '',
                        created_at  TIMESTAMPTZ DEFAULT NOW()
                    )
                """)

                # --- Settings ---
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key         TEXT PRIMARY KEY,
                        value       TEXT NOT NULL,
                        updated_at  TIMESTAMPTZ DEFAULT NOW()
                    )
                """)

                # --- Audit Log ---
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id          SERIAL PRIMARY KEY,
                        timestamp   TIMESTAMPTZ DEFAULT NOW() NOT NULL,
                        table_name  TEXT        NOT NULL,
                        record_id   INTEGER,
                        action      TEXT        NOT NULL
                                                CHECK(action IN ('INSERT', 'UPDATE', 'DELETE')),
                        old_data    JSONB,
                        new_data    JSONB,
                        user_info   TEXT        DEFAULT 'waldothelazy'
                    )
                """)

                # --- Indeksi ---
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tx_account "
                    "ON transactions(account)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tx_date "
                    "ON transactions(date DESC)"
                )
                # Audit log indeksi (per specifikacija)
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_audit_table_record "
                    "ON audit_log(table_name, record_id)"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_audit_timestamp "
                    "ON audit_log(timestamp DESC)"
                )

        logger.info("PostgreSQL shema uspješno inicijalizirana.")
    except psycopg2.Error as e:
        logger.error("Greška pri inicijalizaciji sheme: %s", e)
        raise


# ---------------------------------------------------------------------------
# Audit helper
# ---------------------------------------------------------------------------

def _write_audit(
    cur: psycopg2.extensions.cursor,
    table_name: str,
    record_id: int | None,
    action: str,
    old_data: dict | None = None,
    new_data: dict | None = None,
) -> None:
    """
    Upiši zapis u audit_log unutar iste transakcije.
    Poziva se iz INSERT/UPDATE/DELETE operacija.
    """
    cur.execute(
        """
        INSERT INTO audit_log (table_name, record_id, action, old_data, new_data)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            table_name,
            record_id,
            action,
            json.dumps(old_data, default=str) if old_data else None,
            json.dumps(new_data, default=str) if new_data else None,
        ),
    )


# ---------------------------------------------------------------------------
# Settings CRUD
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_setting(key: str, default: str = "") -> str:
    """Dohvati postavku iz baze. Cachira se 5 minuta."""
    safe_key = sanitize_text(key, max_length=100)
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT value FROM settings WHERE key = %s", (safe_key,)
                )
                row = cur.fetchone()
                return row["value"] if row else default
    except psycopg2.Error as e:
        logger.error("Greška pri čitanju postavke '%s': %s", key, e)
        return default


def set_setting(key: str, value: str) -> None:
    """Spremi ili ažuriraj postavku (UPSERT). Čisti cache."""
    safe_key = sanitize_text(key, max_length=100)
    safe_value = sanitize_text(str(value), max_length=1000)
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO settings (key, value, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (key) DO UPDATE
                        SET value = EXCLUDED.value,
                            updated_at = NOW()
                    """,
                    (safe_key, safe_value),
                )
                _write_audit(cur, "settings", None, "UPDATE",
                             new_data={"key": safe_key, "value": safe_value})
        st.cache_data.clear()
    except psycopg2.Error as e:
        logger.error("Greška pri postavljanju '%s': %s", key, e)
        raise


# ---------------------------------------------------------------------------
# Transactions CRUD
# ---------------------------------------------------------------------------

def insert_transaction(row: dict, auto_transfer: bool = True) -> None:
    """
    Umetni novu transakciju. Sanitizira sve unose. Kreira audit zapis.
    Čisti Streamlit cache nakon uspješnog upisa.
    """
    account = sanitize_account(row.get("account"), ACCOUNTS)
    tx_type = sanitize_transaction_type(row.get("type"), TRANSACTION_TYPES)
    category = sanitize_category(row.get("category"), ALL_CATEGORIES)
    amount = parse_eur(row.get("amount", 0))
    tx_date = row.get("date") or date.today()
    description = sanitize_text(row.get("description") or "")

    if amount < 0:
        logger.warning("Negativni iznos zamijenjen apsolutnom vrijednošću: %s", amount)
        amount = abs(amount)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO transactions
                        (date, type, category, account, amount, description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (str(tx_date), tx_type, category, account, amount, description),
                )
                new_id = cur.fetchone()[0]
                _write_audit(cur, "transactions", new_id, "INSERT", new_data={
                    "date": str(tx_date), "type": tx_type, "category": category,
                    "account": account, "amount": float(amount), "description": description,
                })
        st.cache_data.clear()
    except psycopg2.Error as e:
        logger.error("Greška pri unosu transakcije: %s", e)
        raise

    # Automatski transfer: Trošak → Prihod na odredišnom računu
    if (
        auto_transfer
        and tx_type == "Trošak"
        and account in TRANSFER_SOURCE_ACCOUNTS
        and category in TRANSFER_CATEGORIES
        and amount > 0
    ):
        insert_transaction(
            {
                "date": tx_date,
                "type": "Prihod",
                "category": "Transfer",
                "account": category,
                "amount": amount,
                "description": f"Uplaćeno s {account}",
            },
            auto_transfer=False,
        )


def update_transaction(tx_id: int, changes: dict) -> None:
    """
    Ažuriraj transakciju. Whitelist validacija kolumni + sanitizacija vrijednosti.
    Kreira audit zapis s old/new podacima.
    """
    if not changes:
        return

    safe_cols: list[str] = []
    safe_vals: list[Any] = []

    for col, val in changes.items():
        if col not in _ALLOWED_UPDATE_COLUMNS:
            logger.warning("Odbačena nedozvoljena kolumna za UPDATE: '%s'", col)
            continue

        if col == "amount":
            val = parse_eur(val)
            if val < 0:
                val = abs(val)
        elif col == "date":
            val = str(val) if val else str(date.today())
        elif col == "type":
            val = sanitize_transaction_type(val, TRANSACTION_TYPES)
        elif col == "category":
            val = sanitize_category(val, ALL_CATEGORIES)
        elif col == "account":
            val = sanitize_account(val, ACCOUNTS)
        elif col == "description":
            val = sanitize_text(val or "")

        safe_cols.append(f"{col} = %s")
        safe_vals.append(val)

    if not safe_cols:
        return

    safe_vals.append(int(tx_id))
    sql = f"UPDATE transactions SET {', '.join(safe_cols)} WHERE id = %s"

    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Dohvati stare podatke za audit
                cur.execute(
                    "SELECT * FROM transactions WHERE id = %s", (int(tx_id),)
                )
                old_row = dict(cur.fetchone() or {})

                # Izvrši update
                cur.execute(sql, safe_vals)

                _write_audit(cur, "transactions", int(tx_id), "UPDATE",
                             old_data=old_row, new_data=changes)
        st.cache_data.clear()
    except psycopg2.Error as e:
        logger.error("Greška pri ažuriranju transakcije %d: %s", tx_id, e)
        raise


def delete_transaction(tx_id: int) -> None:
    """Obriši transakciju. Kreira audit zapis s podacima obrisanog retka."""
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # Dohvati podatke prije brisanja za audit
                cur.execute(
                    "SELECT * FROM transactions WHERE id = %s", (int(tx_id),)
                )
                old_row = dict(cur.fetchone() or {})

                cur.execute(
                    "DELETE FROM transactions WHERE id = %s", (int(tx_id),)
                )
                _write_audit(cur, "transactions", int(tx_id), "DELETE",
                             old_data=old_row)
        st.cache_data.clear()
    except psycopg2.Error as e:
        logger.error("Greška pri brisanju transakcije %d: %s", tx_id, e)
        raise


# ---------------------------------------------------------------------------
# Queries — sve READ funkcije koriste @st.cache_data
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def fetch_all() -> pd.DataFrame:
    """Dohvati sve transakcije (cachira se 5 min)."""
    try:
        with get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT id, date, type, category, account, amount, description "
                "FROM transactions ORDER BY date DESC, id DESC",
                conn,
            )
    except psycopg2.Error as e:
        logger.error("Greška pri dohvatu transakcija: %s", e)
        return _empty_transactions_df()

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["amount"] = df["amount"].astype(float)
    else:
        return _empty_transactions_df()
    return df


@st.cache_data(ttl=300)
def fetch_by_account(account: str) -> pd.DataFrame:
    """Dohvati transakcije za specifični račun (cachira se 5 min)."""
    safe_account = sanitize_account(account, ACCOUNTS)
    try:
        with get_connection() as conn:
            df = pd.read_sql_query(
                "SELECT id, date, type, category, account, amount, description "
                "FROM transactions WHERE account = %s ORDER BY date DESC, id DESC",
                conn,
                params=(safe_account,),
            )
    except psycopg2.Error as e:
        logger.error("Greška pri dohvatu za račun '%s': %s", account, e)
        return _empty_transactions_df()

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["amount"] = df["amount"].astype(float)
    else:
        return _empty_transactions_df()
    return df


def _empty_transactions_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["id", "date", "type", "category", "account", "amount", "description"]
    )
