"""
WaldosLair — Entry point.

Pokretanje:
    streamlit run main.py

Arhitektura:
    main.py              → entry point (ova datoteka)
    core/config.py       → konstante + .env učitavanje
    core/db.py           → PostgreSQL CRUD + audit log + connection pool
    core/utils.py        → valuta, sanitizacija, citati, email notifikacije
    ui/styles.py         → sav CSS (Dark Star + Wayne teme)
    ui/app.py            → routing, auth, navigacija
    ui/pages/finance.py  → Finance modul (Wayne Enterprises tema)
    logs/                → app.log (automatski kreiran)
"""
import streamlit as st

# Page config mora biti PRVI Streamlit poziv u čitavoj aplikaciji
st.set_page_config(
    page_title="Waldo's Lair",
    page_icon="🏰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from ui.app import run  # noqa: E402 — import nakon set_page_config

if __name__ == "__main__":
    run()
else:
    # Streamlit poziva module direktno, ne uvijek kroz __main__
    run()
