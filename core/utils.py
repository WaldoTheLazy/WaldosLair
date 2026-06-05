"""
WaldosLair — Pomoćne funkcije.

Sadrži:
  - Formatiranje i parsiranje EUR valute u hrvatskom formatu
  - Sanitizacija korisničkih unosa (zaštita od XSS/injection)
  - Dohvaćanje citata (ZenQuotes API + lokalna lista)
  - Email notifikacije pri loginu
"""
from __future__ import annotations

import html
import logging
import random
import re
import smtplib
import unicodedata
from datetime import datetime
from email.mime.text import MIMEText

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_MAX_TEXT_LENGTH = 500


# ---------------------------------------------------------------------------
# Sanitizacija unosa
# ---------------------------------------------------------------------------

def sanitize_text(value: str | None, max_length: int = _MAX_TEXT_LENGTH) -> str:
    """
    Sanitizira korisnički tekstualni unos.
    1. Strip → Unicode NFKC normalizacija → HTML escape → skraćivanje
    """
    if value is None:
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKC", text)
    text = html.escape(text, quote=True)
    return text[:max_length]


def sanitize_amount_text(value: str | None) -> str:
    """Dopušta samo znakove relevantne za iznos valute."""
    if value is None:
        return "0"
    cleaned = re.sub(r"[^\d.,\-\s€]", "", str(value).strip())
    return cleaned[:30]


def sanitize_category(value: str | None, valid_options: list[str]) -> str:
    """Whitelist validacija — vraća 'Ostalo' ako vrijednost nije u listi."""
    if value and value in valid_options:
        return value
    return "Ostalo"


def sanitize_account(value: str | None, valid_accounts: list[str]) -> str:
    """Whitelist validacija računa."""
    if value and value in valid_accounts:
        return value
    return valid_accounts[0] if valid_accounts else ""


def sanitize_transaction_type(value: str | None, valid_types: list[str]) -> str:
    """Whitelist validacija tipa transakcije."""
    if value and value in valid_types:
        return value
    return valid_types[0] if valid_types else "Trošak"


# ---------------------------------------------------------------------------
# Formatiranje valute — Hrvatski format (1.234,56 €)
# ---------------------------------------------------------------------------

def format_eur(amount) -> str:
    """
    Formatira float kao hrvatsku valutu: 1.234,56 €

    Primjeri:
        format_eur(1234.56)  → '1.234,56 €'
        format_eur(None)     → '0,00 €'
    """
    if amount is None or (isinstance(amount, float) and pd.isna(amount)):
        return "0,00 €"
    try:
        val = float(amount)
    except (TypeError, ValueError):
        return "0,00 €"
    s = f"{val:,.2f}"
    s = s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return f"{s} €"


def parse_eur(text) -> float:
    """
    Parsira tekst u format HR valute i vraća float.
    Prihvaća: '1.234,56', '1.234,56 €', '100', 100, 100.5, None
    """
    if text is None:
        return 0.0
    if isinstance(text, (int, float)):
        try:
            if pd.isna(text):
                return 0.0
        except (TypeError, ValueError):
            pass
        return float(text)

    s = sanitize_amount_text(str(text))
    s = s.replace("€", "").replace(" ", "").replace("\xa0", "")
    if not s:
        return 0.0

    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "." in s:
        parts = s.split(".")
        head = parts[0].lstrip("-")
        if head.isdigit() and len(parts) >= 2 and all(
            p.isdigit() and len(p) == 3 for p in parts[1:]
        ):
            s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Citati
# ---------------------------------------------------------------------------

def get_quote() -> dict[str, str]:
    """
    Dohvati citat: 50% šansa od ZenQuotes API-ja, 50% od lokalne liste.
    Svaki poziv vraća novi citat (ne cachira se — per specifikacija).
    """
    # Lazy import da izbjegnemo circular import s config
    from core.config import POP_CULTURE_QUOTES

    if random.random() < 0.5:
        try:
            r = requests.get("https://zenquotes.io/api/random", timeout=4)
            r.raise_for_status()
            data = r.json()
            return {
                "text": sanitize_text(data[0]["q"]),
                "author": sanitize_text(data[0]["a"]),
            }
        except Exception:
            pass

    return random.choice(POP_CULTURE_QUOTES)


# ---------------------------------------------------------------------------
# Email notifikacije pri loginu
# ---------------------------------------------------------------------------

def send_login_notification(ip_address: str = "nepoznata") -> None:
    """
    Šalje email obavijest pri uspješnom loginu.
    Poziva se samo ako su SMTP varijable postavljene u .env.
    Greške se logiraju ali NE prekidaju login flow.
    """
    from core.config import (
        EMAIL_NOTIFICATIONS_ENABLED,
        NOTIFY_EMAIL,
        SMTP_HOST,
        SMTP_PASS,
        SMTP_PORT,
        SMTP_USER,
    )

    if not EMAIL_NOTIFICATIONS_ENABLED:
        return

    try:
        now = datetime.now().strftime("%d.%m.%Y u %H:%M:%S")
        body = (
            f"🏰 WaldosLair — Uspješna prijava\n\n"
            f"Korisnik WaldoTheLazy prijavio se {now}.\n"
            f"IP adresa: {ip_address}\n\n"
            f"Ako ovo nisi bio ti, odmah promijeni lozinku!"
        )
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = "🔐 WaldosLair — Login Alert"
        msg["From"] = SMTP_USER
        msg["To"] = NOTIFY_EMAIL

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [NOTIFY_EMAIL], msg.as_string())

        logger.info("Login notifikacija uspješno poslana na %s", NOTIFY_EMAIL)
    except Exception as e:
        logger.error("Greška pri slanju login notifikacije: %s", e)
        # Ne bacamo iznimku — login ne smije biti blokiran zbog emaila


# ---------------------------------------------------------------------------
# Pomoćne math funkcije
# ---------------------------------------------------------------------------

def safe_int(text: str, default: int, min_value: int = 0) -> int:
    """Parsira int iz korisničkog teksta. Vraća default za nevaljane unose."""
    try:
        v = int(float(str(text).strip().replace(",", ".")))
        return v if v >= min_value else default
    except (ValueError, TypeError):
        return default
