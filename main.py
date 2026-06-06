"""
WaldosLair — Glavni entry point.

Pokretanje aplikacije:
    streamlit run main.py

Arhitektura:
    main.py           → routing, auth, navigacija (ova datoteka)
    config.py         → sve konstante, kategorije, lozinka (iz .env)
    styles.py         → sav CSS
    utils.py          → format_eur, parse_eur, sanitizacija, citati
    database.py       → sav SQL (parametrizirani upiti, WAL mode)
    finance_ui.py     → Streamlit UI za Finance modul
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Osiguraj da Python uvijek pronađe module u direktoriju aplikacije,
# bez obzira odakle Streamlit pokreće skriptu.
# ---------------------------------------------------------------------------
_APP_DIR = Path(__file__).parent.resolve()
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

import streamlit as st

from config import ACCESS_CODE, NAV_PAGES
from finance_ui import get_finance_dashboard_metrics, render as render_finance
from styles import DARK_STAR_CSS
from utils import format_eur, get_quote

# ---------------------------------------------------------------------------
# Logging konfiguracija
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Streamlit page config — mora biti PRVI Streamlit poziv
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Waldo's Lair",
    page_icon="🏰",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# Sigurna provjera lozinke (timing-safe usporedba)
# ---------------------------------------------------------------------------

def _check_access_code(submitted_code: str) -> bool:
    """
    Provjeri access code koristeći timing-safe usporedbu.
    Koristi hmac.compare_digest() — sprječava timing napade.
    """
    if not submitted_code or not ACCESS_CODE:
        return False
    return hmac.compare_digest(
        submitted_code.encode("utf-8"),
        ACCESS_CODE.encode("utf-8"),
    )


def _make_session_token() -> str:
    """Generiraj jednokratni session token za ovu sesiju."""
    import secrets
    return secrets.token_urlsafe(32)


def _is_token_valid(token: str) -> bool:
    """Provjeri je li token pohranjen u session_state (ista browser sesija)."""
    return (
        token
        and "auth_token" in st.session_state
        and hmac.compare_digest(token, st.session_state.get("auth_token", ""))
    )


# ---------------------------------------------------------------------------
# Session state inicijalizacija
# ---------------------------------------------------------------------------

def _init_session_state() -> None:
    """
    Inicijaliziraj session state.
    logged_in se obnavlja iz query_params tokena — preživljava F5 refresh
    unutar iste browser sesije (tab ostaje otvoren).
    """
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = NAV_PAGES[0][0]
    if "login_attempts" not in st.session_state:
        st.session_state["login_attempts"] = 0

    # Pokušaj obnoviti login iz URL tokena (preživljava page refresh)
    if not st.session_state["logged_in"]:
        token_from_url = st.query_params.get("t", "")
        if token_from_url and _is_token_valid(token_from_url):
            st.session_state["logged_in"] = True


# ---------------------------------------------------------------------------
# Stranica: Landing / Login
# ---------------------------------------------------------------------------

def show_landing() -> None:
    """Star Wars themed landing stranica s zaštitom pristupa."""
    st.markdown(DARK_STAR_CSS, unsafe_allow_html=True)
    st.markdown("""
    <div class="hero-container" style="min-height: 60vh; padding-bottom: 1rem;">
        <div class="hero-title">WALDO'S LAIR</div>
        <div class="hero-separator"></div>
        <div class="hero-subtitle">
            A long time ago in a galaxy far, far away...<br>
            Waldo The Lazy needed a central hub.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Ograničenje pokušaja prijave (rate limiting na UI razini)
    MAX_ATTEMPTS = 10
    if st.session_state.login_attempts >= MAX_ATTEMPTS:
        st.error("⛔ Previše neuspješnih pokušaja. Osvježi stranicu da pokušaš ponovo.")
        logger.warning("Maksimalni broj pokušaja prijave dostignut.")
        return

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        with st.form("login_form", clear_on_submit=False):
            code = st.text_input(
                "Enter Access Code",
                type="password",
                placeholder="••••••••",
                label_visibility="visible",
            )
            submitted = st.form_submit_button("⚔  Enter Lair", use_container_width=True)

        if submitted:
            if _check_access_code(code):
                token = _make_session_token()
                st.session_state.logged_in = True
                st.session_state.auth_token = token
                st.session_state.login_attempts = 0
                # Spremi token u URL — preživljava F5 unutar iste browser sesije
                st.query_params["t"] = token
                logger.info("Uspješna prijava.")
                st.rerun()
            else:
                st.session_state.login_attempts += 1
                remaining = MAX_ATTEMPTS - st.session_state.login_attempts
                st.error(
                    f"⛔ Access Denied. The Force is not with you. "
                    f"({remaining} pokušaja ostalo)"
                )
                logger.warning(
                    "Neuspješan pokušaj prijave. Ukupno: %d",
                    st.session_state.login_attempts,
                )


# ---------------------------------------------------------------------------
# Dashboard: Persistentni header (quote + datum)
# ---------------------------------------------------------------------------

def render_persistent_header() -> None:
    """Welcome header s datumom i svježi citat na svakom refreshu."""
    today = datetime.now().strftime("%A, %B %d %Y")
    st.markdown(
        f'<div class="welcome-header">Welcome back, Waldo.</div>'
        f'<div class="welcome-sub">{today}</div>',
        unsafe_allow_html=True,
    )

    # Novi citat na svakom refreshu — ne pohranjujemo u session_state
    q = get_quote()
    col_q, col_btn = st.columns([6, 1])
    with col_q:
        st.markdown(
            f'<div class="quote-box">'
            f'"{q["text"]}"'
            f'<div class="quote-author">— {q["author"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("↻ New", help="Novi citat", key="header_new_quote"):
            st.rerun()


# ---------------------------------------------------------------------------
# Dashboard: Navigacija
# ---------------------------------------------------------------------------

def render_top_nav() -> None:
    """Horizontalni gumbi za navigaciju između modula."""
    cols = st.columns(len(NAV_PAGES))
    for col, (label, _) in zip(cols, NAV_PAGES):
        with col:
            is_active = st.session_state.current_page == label
            if st.button(
                label,
                key=f"nav_{label}",
                type="primary" if is_active else "secondary",
                use_container_width=True,
            ):
                st.session_state.current_page = label
                st.rerun()


# ---------------------------------------------------------------------------
# Stranice modula
# ---------------------------------------------------------------------------

def show_home() -> None:
    """Glavni Dashboard — Quick Status kartice za sve module."""
    st.markdown("""
    <div style="font-family:'Orbitron',monospace;font-size:0.8rem;color:#7878a0;
                letter-spacing:0.15em;text-transform:uppercase;margin-bottom:1rem;">
        Quick Status
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        try:
            m = get_finance_dashboard_metrics()
            tone = "#6cd49a" if m["trenutno_stanje"] >= 0 else "#ff7878"
            proj_tone = "#6cd49a" if m["predvideno_stanje"] >= 0 else "#ff7878"
            st.markdown(f"""
            <div class="card">
                <div class="card-icon">💰</div>
                <div class="card-title">Osobne Financije</div>
                <div style="font-family:'Rajdhani',sans-serif;text-align:left;
                            margin-top:0.4rem;line-height:1.55;font-size:0.92rem;">
                    <div style="color:#7a8aa8;font-size:0.7rem;letter-spacing:0.14em;
                                text-transform:uppercase;">Trenutno stanje</div>
                    <div style="color:{tone};font-family:'Orbitron',monospace;
                                font-weight:700;font-size:1.15rem;margin-bottom:0.5rem;">
                        {format_eur(m["trenutno_stanje"])}
                    </div>
                    <div style="color:#7a8aa8;font-size:0.7rem;letter-spacing:0.14em;
                                text-transform:uppercase;">Troškovi ovaj mjesec</div>
                    <div style="color:#ff7878;font-family:'Orbitron',monospace;
                                font-weight:700;font-size:1.05rem;margin-bottom:0.5rem;">
                        {format_eur(m["troskovi_mjesec"])}
                    </div>
                    <div style="color:#7a8aa8;font-size:0.7rem;letter-spacing:0.14em;
                                text-transform:uppercase;">Predviđeno stanje</div>
                    <div style="color:{proj_tone};font-family:'Orbitron',monospace;
                                font-weight:700;font-size:1.05rem;">
                        {format_eur(m["predvideno_stanje"])}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            logger.error("Greška pri učitavanju finance metrike: %s", e)
            st.markdown("""
            <div class="card">
                <div class="card-icon">💰</div>
                <div class="card-title">Osobne Financije</div>
                <div class="card-status" style="color:#ff7878;">Greška pri učitavanju</div>
            </div>
            """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="card">
            <div class="card-icon">🍲</div>
            <div class="card-title">Meal Planner</div>
            <div class="card-status">Lembas Bread</div>
            <div class="card-badge">🧝 Elven Rations</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown("""
        <div class="card">
            <div class="card-icon">📡</div>
            <div class="card-title">Tech Scene</div>
            <div class="card-status">3 new tech updates today</div>
            <div class="card-badge">🔴 Live</div>
        </div>
        """, unsafe_allow_html=True)


def show_finance() -> None:
    render_finance()


def show_meals() -> None:
    st.markdown("""
    <div class="subapp-container" style="
        background: linear-gradient(135deg, #0a110a 0%, #0d150d 40%, #0a0f08 100%);
        border: 1px solid rgba(100,160,80,0.25);
        box-shadow: inset 0 0 80px rgba(40,80,20,0.15);">
        <div style="font-size:3.5rem;margin-bottom:1rem;">🌿</div>
        <div class="subapp-title" style="color:#7dc25a;text-shadow:0 0 20px rgba(125,194,90,0.4);">
            THE GREEN DRAGON INN
        </div>
        <div class="subapp-subtitle" style="color:#88b868;">
            Meal Planner &nbsp;|&nbsp; Shire Culinary Chronicles
        </div>
        <div style="color:#6a9050;font-family:'Rajdhani',sans-serif;
                    font-size:0.95rem;margin-bottom:2rem;max-width:440px;line-height:1.6;">
            "Even the smallest person can change the course of the future."<br>
            <span style="color:#7dc25a;font-size:0.85rem;">— Galadriel, Lord of the Rings</span>
        </div>
        <div class="under-dev-badge" style="color:#7dc25a;border-color:#7dc25a;
            background:rgba(125,194,90,0.08);">STATUS: UNDER DEVELOPMENT</div>
    </div>
    """, unsafe_allow_html=True)


def show_workout() -> None:
    st.markdown("""
    <div class="subapp-container" style="
        background: linear-gradient(135deg, #150808 0%, #1a0a0a 40%, #120808 100%);
        border: 1px solid rgba(200,50,50,0.25);
        box-shadow: inset 0 0 80px rgba(180,30,30,0.1);">
        <div style="font-size:3.5rem;margin-bottom:1rem;">⚡</div>
        <div class="subapp-title" style="color:#e84040;text-shadow:0 0 20px rgba(232,64,64,0.5);">
            STARK TRAINING PROTOCOL
        </div>
        <div class="subapp-subtitle" style="color:#c06060;">
            Workout Plan &nbsp;|&nbsp; Avengers Initiative
        </div>
        <div style="color:#905050;font-family:'Rajdhani',sans-serif;
                    font-size:0.95rem;margin-bottom:2rem;max-width:440px;line-height:1.6;">
            "Part of the journey is the end."<br>
            <span style="color:#e84040;font-size:0.85rem;">— Tony Stark, Avengers: Endgame</span>
        </div>
        <div class="under-dev-badge" style="color:#e84040;border-color:#e84040;
            background:rgba(232,64,64,0.08);">STATUS: UNDER DEVELOPMENT</div>
    </div>
    """, unsafe_allow_html=True)


def show_woodworking() -> None:
    st.markdown("""
    <div class="subapp-container" style="
        background: linear-gradient(135deg, #120d08 0%, #160f0a 40%, #100c07 100%);
        border: 1px solid rgba(180,130,60,0.25);
        box-shadow: inset 0 0 80px rgba(140,90,30,0.12);">
        <div style="font-size:3.5rem;margin-bottom:1rem;">🪵</div>
        <div class="subapp-title" style="color:#c8922a;text-shadow:0 0 20px rgba(200,146,42,0.4);">
            THE DWARVEN FORGE
        </div>
        <div class="subapp-subtitle" style="color:#aa7830;">
            Woodworking Modeling &nbsp;|&nbsp; Dungeons &amp; Dragons Workshop
        </div>
        <div style="color:#806030;font-family:'Rajdhani',sans-serif;
                    font-size:0.95rem;margin-bottom:2rem;max-width:440px;line-height:1.6;">
            "Not all treasure is silver and gold, mate."<br>
            <span style="color:#c8922a;font-size:0.85rem;">— D&D Dungeon Master's Guide</span>
        </div>
        <div class="under-dev-badge" style="color:#c8922a;border-color:#c8922a;
            background:rgba(200,146,42,0.08);">STATUS: UNDER DEVELOPMENT</div>
    </div>
    """, unsafe_allow_html=True)


def show_tech() -> None:
    st.markdown("""
    <div class="subapp-container" style="
        background: linear-gradient(135deg, #080d15 0%, #0a1020 40%, #080c12 100%);
        border: 1px solid rgba(0,200,255,0.2);
        box-shadow: inset 0 0 80px rgba(0,150,220,0.08);">
        <div style="font-size:3.5rem;margin-bottom:1rem;">📡</div>
        <div class="subapp-title" style="color:#00c8ff;text-shadow:0 0 20px rgba(0,200,255,0.5);">
            TECH INTELLIGENCE HUB
        </div>
        <div class="subapp-subtitle" style="color:#4090b0;">
            Tech Scene News &nbsp;|&nbsp; Galactic Information Network
        </div>
        <div style="color:#305870;font-family:'Rajdhani',sans-serif;
                    font-size:0.95rem;margin-bottom:2rem;max-width:440px;line-height:1.6;">
            "Help me, Obi-Wan Kenobi. You're my only hope."<br>
            <span style="color:#00c8ff;font-size:0.85rem;">— Princess Leia, Star Wars</span>
        </div>
        <div class="under-dev-badge" style="color:#00c8ff;border-color:#00c8ff;
            background:rgba(0,200,255,0.06);">STATUS: UNDER DEVELOPMENT</div>
    </div>
    """, unsafe_allow_html=True)


def show_grocery() -> None:
    st.markdown("""
    <div class="subapp-container" style="
        background: linear-gradient(135deg, #0d0d18 0%, #101018 40%, #0a0a14 100%);
        border: 1px solid rgba(160,100,220,0.22);
        box-shadow: inset 0 0 80px rgba(120,60,200,0.08);">
        <div style="font-size:3.5rem;margin-bottom:1rem;">🛒</div>
        <div class="subapp-title" style="color:#b06cd8;text-shadow:0 0 20px rgba(176,108,216,0.4);">
            CANTINA MARKET
        </div>
        <div class="subapp-subtitle" style="color:#8854aa;">
            Grocery Shopping &amp; Prices &nbsp;|&nbsp; Mos Eisley Trading Post
        </div>
        <div style="color:#604880;font-family:'Rajdhani',sans-serif;
                    font-size:0.95rem;margin-bottom:2rem;max-width:440px;line-height:1.6;">
            "You will never find a more wretched hive of scum and villainy."<br>
            <span style="color:#b06cd8;font-size:0.85rem;">— Obi-Wan Kenobi, Star Wars</span>
        </div>
        <div class="under-dev-badge" style="color:#b06cd8;border-color:#b06cd8;
            background:rgba(176,108,216,0.08);">STATUS: UNDER DEVELOPMENT</div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Routing tablica — mapira label na handler funkciju
# ---------------------------------------------------------------------------

_PAGE_HANDLERS: dict[str, callable] = {
    "🏰 Dashboard":        show_home,
    "💰 Personal Finance": show_finance,
    "🍲 Meal Planner":     show_meals,
    "🏋️ Workout Plan":     show_workout,
    "🪵 Woodworking":      show_woodworking,
    "📡 Tech Scene":       show_tech,
    "🛒 Shopping":         show_grocery,
}


# ---------------------------------------------------------------------------
# Glavni dashboard wrapper
# ---------------------------------------------------------------------------

def show_main_dashboard() -> None:
    """Renderira kompletan dashboard s navbarem i aktivnom stranicom."""
    st.markdown(DARK_STAR_CSS, unsafe_allow_html=True)
    render_persistent_header()
    render_top_nav()
    st.write("---")

    handler = _PAGE_HANDLERS.get(
        st.session_state.current_page, show_home
    )
    handler()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    _init_session_state()

    if not st.session_state.logged_in:
        show_landing()
        return

    show_main_dashboard()


if __name__ == "__main__":
    main()
