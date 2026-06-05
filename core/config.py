"""
WaldosLair — Centralna konfiguracija.

Sve konstante, kategorije i tema aplikacije na jednom mjestu.
Osjetljivi podaci učitavaju se isključivo iz .env datoteke.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent  # ~/waldoslair_app/
ENV_PATH = BASE_DIR / ".env"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

load_dotenv(ENV_PATH)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

ACCESS_CODE: str = os.environ.get("ACCESS_CODE", "")

if not ACCESS_CODE:
    raise EnvironmentError(
        "ACCESS_CODE nije postavljen!\n"
        "Kreiraj .env datoteku s: ACCESS_CODE=tvoja_lozinka\n"
        "Nikad ne commitas .env na GitHub (provjeri .gitignore)."
    )

# ---------------------------------------------------------------------------
# Email notifikacije (opcionalno — za login alertove)
# ---------------------------------------------------------------------------

SMTP_HOST: str = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER: str = os.environ.get("SMTP_USER", "")
SMTP_PASS: str = os.environ.get("SMTP_PASS", "")
NOTIFY_EMAIL: str = os.environ.get("NOTIFY_EMAIL", "")  # adresa primatelja

EMAIL_NOTIFICATIONS_ENABLED: bool = all([SMTP_USER, SMTP_PASS, NOTIFY_EMAIL])

# ---------------------------------------------------------------------------
# PostgreSQL — Baza podataka
# ---------------------------------------------------------------------------

DB_HOST: str = os.environ.get("DB_HOST", "localhost")
DB_PORT: int = int(os.environ.get("DB_PORT", "5432"))
DB_NAME: str = os.environ.get("DB_NAME", "waldoslair_db")
DB_USER: str = os.environ.get("DB_USER", "waldothelazydb")
DB_PASS: str = os.environ.get("DB_PASS", "")

if not DB_PASS:
    raise EnvironmentError(
        "DB_PASS nije postavljen!\n"
        "U .env datoteci postavi: DB_PASS=lozinka_baze"
    )

# DSN string za psycopg2
DB_DSN: str = (
    f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
    f"user={DB_USER} password={DB_PASS} "
    "connect_timeout=10 application_name=waldoslair"
)

# ---------------------------------------------------------------------------
# Finance — Računi
# ---------------------------------------------------------------------------

ACCOUNTS: list[str] = [
    "Tekući račun",
    "MasterCard Kreditni",
    "Keks",
    "Revolut",
    "Njivice",
]

# ---------------------------------------------------------------------------
# Finance — Kategorije troškova
# ---------------------------------------------------------------------------

EXPENSE_CATEGORIES: list[str] = [
    # Svakodnevni život
    "Hrana",
    "Ručak",
    "Kava",
    "Shopping",
    # Stanovanje & Komunalije
    "Režije Bukovac",
    "Režije Njivice",
    "Čišćenje",
    # Prijevoz
    "Auto",
    "Putovanja",
    # Financije
    "Kredit",
    "Bankomat",
    "Keks",     # Transfer kategorija
    "Revolut",  # Transfer kategorija
    # Osobno
    "Zdravlje",
    "Odjeća/Obuća",
    "Tehnologija",
    "Zabava",
    "Pokloni",
    # Ostalo
    "Ostalo",
]

INCOME_CATEGORIES: list[str] = [
    "Plaća",
    "Puni nalozi",
    "Božićnice",
    "Uskrsnice",
    "Regres",
    "Nagrade",
    "Ostalo",
]

TRANSACTION_TYPES: list[str] = ["Prihod", "Trošak"]

ALL_CATEGORIES: list[str] = sorted(
    set(EXPENSE_CATEGORIES + INCOME_CATEGORIES + ["Transfer"])
)

# ---------------------------------------------------------------------------
# Finance — Automatski transfer
# ---------------------------------------------------------------------------

TRANSFER_SOURCE_ACCOUNTS: set[str] = {"Tekući račun", "MasterCard Kreditni"}
TRANSFER_CATEGORIES: set[str] = {"Keks", "Revolut"}

# ---------------------------------------------------------------------------
# Finance — Kredit defaulti
# ---------------------------------------------------------------------------

LOAN_MONTHLY_DEFAULT: float = 540.21
LOAN_TOTAL_DEFAULT: int = 31
LOAN_PAID_DEFAULT: int = 5

# ---------------------------------------------------------------------------
# UI — Pop-culture citati
# ---------------------------------------------------------------------------

POP_CULTURE_QUOTES: list[dict] = [
    # Star Wars
    {"text": "Do. Or do not. There is no try.", "author": "Yoda, Star Wars"},
    {"text": "The Force will be with you, always.", "author": "Obi-Wan Kenobi, Star Wars"},
    {"text": "I find your lack of faith disturbing.", "author": "Darth Vader, Star Wars"},
    {"text": "It's a trap!", "author": "Admiral Ackbar, Star Wars"},
    {"text": "I am your father.", "author": "Darth Vader, Star Wars"},
    {"text": "Help me, Obi-Wan Kenobi. You're my only hope.", "author": "Princess Leia, Star Wars"},
    # DC
    {"text": "Why so serious?", "author": "The Joker, The Dark Knight"},
    {"text": "I'm Batman.", "author": "Bruce Wayne, Batman Begins"},
    # Marvel
    {"text": "With great power comes great responsibility.", "author": "Uncle Ben, Spider-Man"},
    {"text": "I am Iron Man.", "author": "Tony Stark, Avengers: Endgame"},
    {"text": "Assemble.", "author": "Captain America, Avengers: Endgame"},
    {"text": "Part of the journey is the end.", "author": "Tony Stark, Avengers: Endgame"},
    # LOTR
    {"text": "Not all those who wander are lost.", "author": "J.R.R. Tolkien, LOTR"},
    {"text": "All we have to decide is what to do with the time that is given us.", "author": "Gandalf, LOTR"},
    {"text": "Even the smallest person can change the course of the future.", "author": "Galadriel, LOTR"},
    {"text": "Fly, you fools!", "author": "Gandalf, LOTR"},
    {"text": "One does not simply walk into Mordor.", "author": "Boromir, LOTR"},
]

# ---------------------------------------------------------------------------
# Navigacija — svi HUB moduli
# ---------------------------------------------------------------------------

NAV_PAGES: list[tuple[str, str]] = [
    ("🏰 Dashboard",        "show_home"),
    ("💰 Personal Finance", "show_finance"),
    ("🍲 Meal Planner",     "show_meals"),
    ("🏋️ Workout Plan",     "show_workout"),
    ("🪵 Woodworking",      "show_woodworking"),
    ("📡 Tech Scene",       "show_tech"),
    ("🛒 Shopping",         "show_grocery"),
]
