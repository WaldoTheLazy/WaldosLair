"""
WaldosLair — Finance modul UI (Wayne Enterprises / DC Batman tema).

Streamlit UI komponente za Finance modul.
Sav pristup bazi ide isključivo kroz core/db.py.
"""
from __future__ import annotations

import io
import logging
from datetime import date, datetime

import pandas as pd
import streamlit as st

from core.config import (
    ACCOUNTS,
    ALL_CATEGORIES,
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    LOAN_MONTHLY_DEFAULT,
    LOAN_PAID_DEFAULT,
    LOAN_TOTAL_DEFAULT,
    TRANSACTION_TYPES,
)
from core.db import (
    delete_transaction,
    fetch_all,
    fetch_by_account,
    get_setting,
    init_db,
    insert_transaction,
    update_transaction,
)
from core.utils import format_eur, parse_eur, safe_int, sanitize_text
from ui.styles import WAYNE_CSS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# KPI HTML komponenta
# ---------------------------------------------------------------------------

def kpi(label: str, value: str, tone: str = "") -> str:
    css_class = f"kpi-value {tone}".strip()
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{sanitize_text(label)}</div>
        <div class="{css_class}">{sanitize_text(value)}</div>
    </div>
    """


# ---------------------------------------------------------------------------
# Data editor
# ---------------------------------------------------------------------------

def _editor_column_config(account_locked: str | None = None) -> dict:
    return {
        "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
        "date": st.column_config.DateColumn("Datum", format="DD.MM.YYYY", required=True),
        "type": st.column_config.SelectboxColumn("Tip", options=TRANSACTION_TYPES, required=True),
        "category": st.column_config.SelectboxColumn("Kategorija", options=ALL_CATEGORIES, required=True),
        "account": st.column_config.SelectboxColumn(
            "Račun", options=ACCOUNTS, required=True,
            disabled=account_locked is not None,
        ),
        "amount": st.column_config.NumberColumn(
            "Iznos (€)", format="%.2f", required=True, step=0.01, min_value=0.0
        ),
        "description": st.column_config.TextColumn("Opis", width="large"),
    }


def _apply_editor_changes(
    editor_key: str, original_df: pd.DataFrame, account_locked: str | None
) -> bool:
    state = st.session_state.get(editor_key)
    if not state:
        return False
    changed = False

    for idx in state.get("deleted_rows", []) or []:
        try:
            tx_id = int(original_df.iloc[idx]["id"])
            delete_transaction(tx_id)
            changed = True
        except (IndexError, KeyError, ValueError) as e:
            logger.warning("Greška pri brisanju: %s", e)

    for idx, edits in (state.get("edited_rows") or {}).items():
        try:
            tx_id = int(original_df.iloc[int(idx)]["id"])
            update_transaction(tx_id, edits)
            changed = True
        except (IndexError, KeyError, ValueError) as e:
            logger.warning("Greška pri ažuriranju: %s", e)

    for new_row in state.get("added_rows") or []:
        if not new_row:
            continue
        row = dict(new_row)
        if account_locked:
            row["account"] = account_locked
        if not row.get("type"):
            row["type"] = "Trošak"
        if not row.get("category"):
            row["category"] = "Ostalo"
        if "amount" not in row:
            continue
        try:
            insert_transaction(row)
            changed = True
        except Exception as e:
            logger.error("Greška pri unosu: %s", e)
            st.error("Greška pri spremanju transakcije. Pokušaj ponovo.")

    state["deleted_rows"] = []
    state["edited_rows"] = {}
    state["added_rows"] = []
    return changed


def render_editor(
    df: pd.DataFrame,
    editor_key: str,
    account_locked: str | None = None,
    hide_account: bool = False,
) -> None:
    show_df = df.copy()
    if hide_account and "account" in show_df.columns:
        show_df = show_df.drop(columns=["account"])

    column_order = [
        c for c in ["id", "date", "type", "category", "account", "amount", "description"]
        if c in show_df.columns
    ]
    cfg = _editor_column_config(account_locked=account_locked)
    cfg = {k: v for k, v in cfg.items() if k in show_df.columns}

    st.data_editor(
        show_df, key=editor_key, num_rows="dynamic",
        use_container_width=True, hide_index=True,
        column_order=column_order, column_config=cfg,
    )

    if _apply_editor_changes(editor_key, df, account_locked):
        st.rerun()


# ---------------------------------------------------------------------------
# Modal za unos nove transakcije
# ---------------------------------------------------------------------------

@st.dialog("➕ Nova Transakcija", width="large")
def new_transaction_dialog() -> None:
    tx_type = st.segmented_control("Tip", TRANSACTION_TYPES, default="Trošak", key="dlg_type")
    if not tx_type:
        tx_type = "Trošak"

    c1, c2 = st.columns(2)
    with c1:
        account = st.selectbox("Račun", ACCOUNTS, key="dlg_account")
    with c2:
        cats = INCOME_CATEGORIES if tx_type == "Prihod" else EXPENSE_CATEGORIES
        category = st.selectbox("Kategorija", cats, key=f"dlg_category_{tx_type}")

    c3, c4 = st.columns(2)
    with c3:
        tx_date = st.date_input("Datum", value=date.today(), key="dlg_date", format="DD.MM.YYYY")
    with c4:
        amount_text = st.text_input(
            "Iznos (€)", value="0,00", placeholder="npr. 1.234,56",
            help="Format: 1.234,56", key="dlg_amount",
        )

    description = st.text_input("Opis (opcionalno)", key="dlg_desc", max_chars=500)
    parsed = parse_eur(amount_text)
    st.caption(f"Parsirani iznos: **{format_eur(parsed)}**")

    b1, b2 = st.columns(2)
    with b1:
        if st.button("💾 Spremi", type="primary", use_container_width=True, key="dlg_save"):
            if parsed <= 0:
                st.error("⚠️ Iznos mora biti veći od nule.")
            else:
                try:
                    insert_transaction({
                        "date": tx_date, "type": tx_type,
                        "category": category, "account": account,
                        "amount": parsed, "description": description,
                    })
                    st.success("✅ Transakcija uspješno spremljena.")
                    st.rerun()
                except Exception as e:
                    logger.error("Greška pri spremanju transakcije: %s", e)
                    st.error("Došlo je do greške pri komunikaciji s bazom.")
    with b2:
        if st.button("✖ Odustani", use_container_width=True, key="dlg_cancel"):
            st.rerun()


# ---------------------------------------------------------------------------
# Account balance helper
# ---------------------------------------------------------------------------

def _account_balance(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    income = df.loc[df["type"] == "Prihod", "amount"].sum()
    expense = df.loc[df["type"] == "Trošak", "amount"].sum()
    return float(income - expense)


# ---------------------------------------------------------------------------
# Tab rendereri
# ---------------------------------------------------------------------------

def tab_checking() -> None:
    starting = parse_eur(get_setting("starting_balance_tekuci", "0"))

    with st.expander("⚙️ Početno stanje računa", expanded=False):
        c1, c2 = st.columns([3, 1])
        with c1:
            sb_text = st.text_input(
                "Početno stanje (€)", value=format_eur(starting).replace(" €", ""),
                placeholder="npr. 1.234,56", key="sb_tekuci_input",
            )
        with c2:
            st.markdown("<div style='height:1.85rem;'></div>", unsafe_allow_html=True)
            if st.button("💾 Spremi", key="sb_tekuci_save", use_container_width=True):
                from core.db import set_setting
                set_setting("starting_balance_tekuci", str(parse_eur(sb_text)))
                st.rerun()

    df = fetch_by_account("Tekući račun")
    balance = starting + _account_balance(df)
    tone = "pos" if balance >= 0 else "neg"
    st.markdown(kpi("Trenutno stanje", format_eur(balance), tone), unsafe_allow_html=True)
    st.caption(f"Početno stanje: {format_eur(starting)} · Neto transakcija: {format_eur(_account_balance(df))}")
    st.markdown("<div class='wayne-divider'></div>", unsafe_allow_html=True)
    render_editor(df, editor_key="ed_checking", account_locked="Tekući račun", hide_account=True)


def tab_mastercard() -> None:
    today = date.today()
    c1, c2 = st.columns(2)
    with c1:
        start = st.date_input("Od datuma", value=today.replace(day=1), key="mc_start", format="DD.MM.YYYY")
    with c2:
        end = st.date_input("Do datuma", value=today, key="mc_end", format="DD.MM.YYYY")

    df = fetch_by_account("MasterCard Kreditni")
    if not df.empty:
        mask = (
            (pd.to_datetime(df["date"]) >= pd.to_datetime(start))
            & (pd.to_datetime(df["date"]) <= pd.to_datetime(end))
        )
        filtered = df[mask].reset_index(drop=True)
    else:
        filtered = df

    expenses = float(filtered.loc[filtered["type"] == "Trošak", "amount"].sum()) if not filtered.empty else 0.0
    balance = _account_balance(filtered)

    k1, k2 = st.columns(2)
    with k1:
        st.markdown(kpi("Troškovi u rasponu", format_eur(expenses), "neg"), unsafe_allow_html=True)
    with k2:
        st.markdown(kpi("Neto u rasponu", format_eur(balance), "pos" if balance >= 0 else "neg"), unsafe_allow_html=True)

    st.markdown("<div class='wayne-divider'></div>", unsafe_allow_html=True)
    render_editor(filtered, editor_key="ed_mastercard", account_locked="MasterCard Kreditni", hide_account=True)


def _simple_account_tab(account: str, editor_key: str) -> None:
    df = fetch_by_account(account)
    balance = _account_balance(df)
    expenses = float(df.loc[df["type"] == "Trošak", "amount"].sum()) if not df.empty else 0.0
    k1, k2 = st.columns(2)
    with k1:
        st.markdown(kpi("Stanje", format_eur(balance), "pos" if balance >= 0 else "neg"), unsafe_allow_html=True)
    with k2:
        st.markdown(kpi("Ukupni troškovi", format_eur(expenses), "neg"), unsafe_allow_html=True)
    st.markdown("<div class='wayne-divider'></div>", unsafe_allow_html=True)
    render_editor(df, editor_key=editor_key, account_locked=account, hide_account=True)


def tab_keks() -> None:
    _simple_account_tab("Keks", "ed_keks")


def tab_revolut() -> None:
    _simple_account_tab("Revolut", "ed_revolut")


def tab_njivice() -> None:
    df = fetch_by_account("Njivice")
    total = float(df["amount"].sum()) if not df.empty else 0.0
    per_owner = total / 3.0

    k1, k2 = st.columns(2)
    with k1:
        st.markdown(kpi("Ukupni godišnji trošak", format_eur(total), "neg"), unsafe_allow_html=True)
    with k2:
        st.markdown(kpi("Tvoj udio (÷ 3)", format_eur(per_owner), "neg"), unsafe_allow_html=True)

    st.markdown("<div class='wayne-divider'></div>", unsafe_allow_html=True)
    if not df.empty:
        chart_df = df.copy()
        chart_df["month"] = pd.to_datetime(chart_df["date"]).dt.to_period("M").astype(str)
        monthly = chart_df.groupby("month")["amount"].sum().reset_index().sort_values("month")
        st.markdown("**Mjesečni troškovi**")
        st.bar_chart(monthly, x="month", y="amount", color="#4a90d9", height=260)
    else:
        st.info("Još nema podataka za prikaz grafova.")

    st.markdown("<div class='wayne-divider'></div>", unsafe_allow_html=True)
    render_editor(df, editor_key="ed_njivice", account_locked="Njivice", hide_account=True)


def tab_loan() -> None:
    monthly = parse_eur(get_setting("loan_monthly", str(LOAN_MONTHLY_DEFAULT))) or LOAN_MONTHLY_DEFAULT
    total = safe_int(get_setting("loan_total", str(LOAN_TOTAL_DEFAULT)), LOAN_TOTAL_DEFAULT, min_value=1)
    paid = max(0, min(total, safe_int(get_setting("loan_paid", str(LOAN_PAID_DEFAULT)), LOAN_PAID_DEFAULT, min_value=0)))

    remaining_installments = max(0, total - paid)
    remaining_amount = remaining_installments * monthly
    pct = (paid / total) if total > 0 else 0.0

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(kpi("Mjesečni anuitet", format_eur(monthly)), unsafe_allow_html=True)
    with k2:
        st.markdown(kpi("Preostali iznos", format_eur(remaining_amount), "neg"), unsafe_allow_html=True)
    with k3:
        st.markdown(kpi("Preostalih rata", str(remaining_installments)), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-family:Rajdhani,sans-serif;color:#8aabcc;letter-spacing:0.1em;"
        f"text-transform:uppercase;font-size:0.85rem;margin-bottom:0.4rem;'>"
        f"Plaćeno {paid}/{total} rata &nbsp;·&nbsp; {pct * 100:.1f}%</div>",
        unsafe_allow_html=True,
    )
    st.progress(min(max(pct, 0.0), 1.0))


def tab_settings() -> None:
    """Postavke Finance modula — početno stanje računa i podaci o kreditu."""
    st.markdown("### ⚙️ Postavke Financijskog Modula")
    st.markdown("<div class='wayne-divider'></div>", unsafe_allow_html=True)

    from core.db import set_setting

    # --- Početno stanje ---
    st.markdown("**Tekući račun — Početno stanje**")
    starting = parse_eur(get_setting("starting_balance_tekuci", "0"))
    c1, c2 = st.columns([3, 1])
    with c1:
        sb_text = st.text_input(
            "Početno stanje (€)", value=format_eur(starting).replace(" €", ""),
            key="settings_sb_tekuci", placeholder="npr. 1.234,56",
            help="Stanje računa prije bilo kakvih transakcija u sustavu.",
        )
    with c2:
        st.markdown("<div style='height:1.85rem;'></div>", unsafe_allow_html=True)
        if st.button("💾 Spremi stanje", key="settings_sb_save", use_container_width=True):
            set_setting("starting_balance_tekuci", str(parse_eur(sb_text)))
            st.success("✅ Početno stanje spremljeno.")
            st.rerun()

    st.markdown("<div class='wayne-divider'></div>", unsafe_allow_html=True)

    # --- Kredit postavke ---
    st.markdown("**Postavke kredita**")
    monthly = parse_eur(get_setting("loan_monthly", str(LOAN_MONTHLY_DEFAULT))) or LOAN_MONTHLY_DEFAULT
    total = safe_int(get_setting("loan_total", str(LOAN_TOTAL_DEFAULT)), LOAN_TOTAL_DEFAULT, min_value=1)
    paid = max(0, min(total, safe_int(get_setting("loan_paid", str(LOAN_PAID_DEFAULT)), LOAN_PAID_DEFAULT)))

    c1, c2, c3 = st.columns(3)
    with c1:
        m_text = st.text_input("Mjesečni anuitet (€)", value=format_eur(monthly).replace(" €", ""), key="settings_loan_m")
    with c2:
        t_text = st.text_input("Ukupan broj rata", value=str(total), key="settings_loan_t")
    with c3:
        p_text = st.text_input("Broj uplaćenih rata", value=str(paid), key="settings_loan_p")

    if st.button("💾 Spremi postavke kredita", key="settings_loan_save", type="primary"):
        set_setting("loan_monthly", str(parse_eur(m_text)))
        set_setting("loan_total", str(safe_int(t_text, LOAN_TOTAL_DEFAULT, min_value=1)))
        set_setting("loan_paid", str(safe_int(p_text, LOAN_PAID_DEFAULT, min_value=0)))
        st.success("✅ Postavke kredita spremljene.")
        st.rerun()


def tab_reports() -> None:
    df = fetch_all()
    sub_tabs = st.tabs(["📅 Tjedni pregled", "🗓️ Mjesečni sažetak", "📚 Master Ledger", "⬇️ Export"])

    with sub_tabs[0]:
        if df.empty:
            st.info("Nema podataka za tjedni pregled.")
        else:
            wdf = df.copy()
            wdf["date"] = pd.to_datetime(wdf["date"])
            wdf["week"] = wdf["date"].dt.to_period("W-SUN").apply(lambda p: p.start_time.date()).astype(str)
            grouped = wdf.groupby("week").apply(
                lambda g: pd.Series({
                    "Prihodi": g.loc[g["type"] == "Prihod", "amount"].sum(),
                    "Troškovi": g.loc[g["type"] == "Trošak", "amount"].sum(),
                })
            ).reset_index()
            grouped["Neto"] = grouped["Prihodi"] - grouped["Troškovi"]
            display = grouped.copy()
            for col in ["Prihodi", "Troškovi", "Neto"]:
                display[col] = display[col].apply(format_eur)
            st.dataframe(display, hide_index=True, use_container_width=True)
            st.bar_chart(grouped.set_index("week")[["Prihodi", "Troškovi"]], height=280)

    with sub_tabs[1]:
        if df.empty:
            st.info("Nema podataka za mjesečni sažetak.")
        else:
            mdf = df.copy()
            mdf["month"] = pd.to_datetime(mdf["date"]).dt.to_period("M").astype(str)
            months = sorted(mdf["month"].unique(), reverse=True)
            chosen = st.selectbox("Odaberi mjesec", months, key="rep_month")
            month_df = mdf[mdf["month"] == chosen]
            inc = float(month_df.loc[month_df["type"] == "Prihod", "amount"].sum())
            exp = float(month_df.loc[month_df["type"] == "Trošak", "amount"].sum())
            net = inc - exp
            k1, k2, k3 = st.columns(3)
            with k1:
                st.markdown(kpi("Prihodi", format_eur(inc), "pos"), unsafe_allow_html=True)
            with k2:
                st.markdown(kpi("Troškovi", format_eur(exp), "neg"), unsafe_allow_html=True)
            with k3:
                st.markdown(kpi("Neto", format_eur(net), "pos" if net >= 0 else "neg"), unsafe_allow_html=True)
            st.markdown("<div class='wayne-divider'></div>", unsafe_allow_html=True)
            by_cat = month_df.groupby(["type", "category"])["amount"].sum().reset_index()
            if not by_cat.empty:
                disp = by_cat.copy()
                disp["amount"] = disp["amount"].apply(format_eur)
                disp.columns = ["Tip", "Kategorija", "Iznos"]
                st.dataframe(disp, hide_index=True, use_container_width=True)

    with sub_tabs[2]:
        st.markdown("**Kompletan povijesni zapis (editable)**")
        render_editor(df, editor_key="ed_master", account_locked=None, hide_account=False)

    with sub_tabs[3]:
        if df.empty:
            st.info("Nema podataka za export.")
        else:
            buf = io.StringIO()
            df.to_csv(buf, index=False)
            st.download_button(
                "⬇️ Preuzmi CSV", data=buf.getvalue(),
                file_name=f"waldo_finance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv", type="primary",
            )


# ---------------------------------------------------------------------------
# Javna metrika za Dashboard karticu
# ---------------------------------------------------------------------------

def get_finance_dashboard_metrics() -> dict:
    """Vrati financijske KPI-je za Dashboard karticu."""
    init_db()
    starting = parse_eur(get_setting("starting_balance_tekuci", "0"))
    df = fetch_all()
    today = date.today()

    if df.empty:
        return {"trenutno_stanje": float(starting), "troskovi_mjesec": 0.0, "predvideno_stanje": float(starting)}

    dates = pd.to_datetime(df["date"])
    month_mask = (dates.dt.year == today.year) & (dates.dt.month == today.month)

    tek = df[df["account"] == "Tekući račun"]
    tek_income = float(tek.loc[tek["type"] == "Prihod", "amount"].sum())
    tek_expense = float(tek.loc[tek["type"] == "Trošak", "amount"].sum())
    trenutno = float(starting) + tek_income - tek_expense

    troskovi = float(df.loc[month_mask & (df["type"] == "Trošak"), "amount"].sum())
    mc_pending = float(df.loc[
        month_mask & (df["account"] == "MasterCard Kreditni") & (df["type"] == "Trošak"),
        "amount"
    ].sum())

    return {"trenutno_stanje": trenutno, "troskovi_mjesec": troskovi, "predvideno_stanje": trenutno - mc_pending}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render() -> None:
    init_db()
    st.markdown(WAYNE_CSS, unsafe_allow_html=True)
    st.markdown(
        "<div class='wayne-header'>🦇 WAYNE ENTERPRISES</div>"
        "<div class='wayne-sub'>Personal Finance Division · Gotham Financial Hub</div>",
        unsafe_allow_html=True,
    )

    if st.button("➕ Nova Transakcija", type="primary"):
        new_transaction_dialog()

    tabs = st.tabs([
        "🦇 Tekući Račun",
        "💳 MasterCard Kreditni",
        "🍪 Keks",
        "🌍 Revolut",
        "🏖️ Troškovi Njivice",
        "🏦 Kredit",
        "📊 Reporti",
        "⚙️ Postavke",
    ])
    with tabs[0]: tab_checking()
    with tabs[1]: tab_mastercard()
    with tabs[2]: tab_keks()
    with tabs[3]: tab_revolut()
    with tabs[4]: tab_njivice()
    with tabs[5]: tab_loan()
    with tabs[6]: tab_reports()
    with tabs[7]: tab_settings()
