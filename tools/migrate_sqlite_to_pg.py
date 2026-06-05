"""
WaldosLair — Migracija SQLite → PostgreSQL.

Ova skripta jednom prenosi podatke iz stare finance.db u novu PostgreSQL bazu.

Pokretanje (iz korijenskog direktorija):
    python tools/migrate_sqlite_to_pg.py --sqlite finance.db

VAŽNO:
    - Pokreni tek NAKON što si kreirao PostgreSQL bazu i inicijalizirao shemu
    - Pokreni init_db() jednom ručno ili pokreni aplikaciju pa odmah zatvori
    - Skripta ne briše staru SQLite bazu — ona ostaje kao backup
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

# Dodaj root direktorij u Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
import psycopg2.extras

from core.config import DB_DSN


def migrate(sqlite_path: str) -> None:
    sqlite_db = Path(sqlite_path)
    if not sqlite_db.exists():
        print(f"❌ SQLite datoteka ne postoji: {sqlite_path}")
        sys.exit(1)

    print(f"📂 Čitam SQLite bazu: {sqlite_path}")

    # Spoji se na SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    # Dohvati sve transakcije
    transactions = sqlite_conn.execute(
        "SELECT date, type, category, account, amount, description FROM transactions ORDER BY id"
    ).fetchall()

    # Dohvati sve postavke
    settings = sqlite_conn.execute("SELECT key, value FROM settings").fetchall()
    sqlite_conn.close()

    print(f"📊 Pronađeno {len(transactions)} transakcija i {len(settings)} postavki.")

    if not transactions and not settings:
        print("ℹ️  Nema podataka za migraciju.")
        return

    # Spoji se na PostgreSQL
    print("🐘 Spajam se na PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(dsn=DB_DSN)
    except psycopg2.Error as e:
        print(f"❌ Greška pri spajanju na PostgreSQL: {e}")
        sys.exit(1)

    try:
        with pg_conn:
            with pg_conn.cursor() as cur:
                # Migracija transakcija
                if transactions:
                    print("💾 Migriram transakcije...")
                    psycopg2.extras.execute_batch(
                        cur,
                        """
                        INSERT INTO transactions (date, type, category, account, amount, description)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        [
                            (
                                row["date"], row["type"], row["category"],
                                row["account"], float(row["amount"]),
                                row["description"] or "",
                            )
                            for row in transactions
                        ],
                        page_size=500,
                    )
                    print(f"   ✅ {len(transactions)} transakcija migriranih.")

                # Migracija postavki
                if settings:
                    print("⚙️  Migriram postavke...")
                    for row in settings:
                        cur.execute(
                            """
                            INSERT INTO settings (key, value)
                            VALUES (%s, %s)
                            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                            """,
                            (row["key"], row["value"]),
                        )
                    print(f"   ✅ {len(settings)} postavki migriranih.")

        print("\n🎉 Migracija uspješno završena!")
        print(f"   SQLite baza ({sqlite_path}) nije obrisana — čuva se kao backup.")

    except psycopg2.Error as e:
        print(f"❌ Greška pri migraciji: {e}")
        pg_conn.rollback()
        sys.exit(1)
    finally:
        pg_conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migracija SQLite → PostgreSQL za WaldosLair")
    parser.add_argument("--sqlite", default="finance.db", help="Putanja do SQLite datoteke")
    args = parser.parse_args()
    migrate(args.sqlite)
