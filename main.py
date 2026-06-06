"""
WaldosLair — Entry point.

Pokretanje:
    streamlit run main.py

Struktura:
    main.py                  → entry point
    core/config.py           → konstante + .env
    core/db.py               → PostgreSQL CRUD + audit log
    core/utils.py            → valuta, sanitizacija, citati, email
    ui/styles.py             → CSS
    ui/app.py                → routing, auth, navigacija
    ui/pages/finance.py      → Finance modul UI
"""
import sys
from pathlib import Path

_APP_DIR = Path(__file__).parent.resolve()
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

import streamlit as st

st.set_page_config(
    page_title="Waldo's Lair",
    page_icon="🏰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from ui.app import run  # noqa: E402

run()
