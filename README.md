# 🏰 WaldosLair

> *"A long time ago in a galaxy far, far away... a Waldo The Lazy needed a central hub."*

Osobni HUB za upravljanje svakodnevnim životom. Aktivni modul: **Personal Finance (Wayne Enterprises / DC Batman tema)**.

---

## 📁 Trenutna struktura projekta

```
waldoslair_app/
├── main.py           # Entry point — streamlit run main.py
│                     # Routing, auth, navigacija, sve stranice HUB-a
│
├── config.py         # Sve konstante i kategorije (učitava .env)
├── database.py       # Sav SQL — PostgreSQL CRUD, audit log, connection pool
├── utils.py          # Valuta (format_eur/parse_eur), sanitizacija, citati, email
├── styles.py         # Sav CSS (Dark Star + Wayne Enterprises teme)
├── finance_ui.py     # Finance modul — kompletan Streamlit UI
│
├── .env              # ⚠️ NIJE u gitu — lokalna datoteka s tajnama
├── .env.example      # Template za .env
├── .gitignore        # Ignorira .env, logs/, *.db
├── requirements.txt  # Python dependencije
└── waldoslair.service # systemd service za produkcijski server
```

---

## 🚀 Pokretanje

### Lokalni razvoj (Windows/Mac/Linux)

```bash
# 1. Kloniraj repozitorij
git clone git@github.com:tvoj-user/waldoslair.git waldoslair_app
cd waldoslair_app

# 2. Kreiraj virtualno okruženje s Python 3.12
python3.12 -m venv venv
source venv/bin/activate        # Linux/Mac
# ili: venv\Scripts\activate    # Windows

# 3. Instaliraj dependencije
pip install -r requirements.txt

# 4. Kreiraj .env
cp .env.example .env
nano .env    # postavi ACCESS_CODE i DB_PASS

# 5. Pokreni
streamlit run main.py
```

### Produkcija (ThinkCentre — waldoslair server)

```bash
# SSH pristup
ssh -p 2222 waldothelazy@192.168.42.105

# Preuzmi najnoviji kod
cd ~/waldoslair_app && git pull

# Instaliraj nove dependencije (ako ih ima)
source venv/bin/activate
pip install -r requirements.txt

# Restart servisa
sudo systemctl restart waldoslair
sudo systemctl status waldoslair

# Praćenje logova u realnom vremenu
sudo journalctl -u waldoslair -f
```

---

## 🔐 Sigurnost

### Implementirane mjere

| Mjera | Gdje | Opis |
|---|---|---|
| `.env` za tajne | `config.py` | `ACCESS_CODE`, `DB_PASS` — nikad hardkodirani u kodu |
| Timing-safe auth | `main.py` | `hmac.compare_digest()` — sprječava timing napade |
| Token auth | `main.py` | `secrets.token_urlsafe(32)` + `st.query_params` — preživljava F5 refresh |
| Rate limiting | `main.py` | Max 10 neuspješnih pokušaja prijave |
| Login email alert | `utils.py` | `send_login_notification()` — SMTP/Gmail obavijest |
| SQL parametrizacija | `database.py` | Svi upiti koriste `%s` placeholdere — nema SQL injection |
| Whitelist UPDATE kolumni | `database.py` | `_ALLOWED_UPDATE_COLUMNS` frozenset |
| Input sanitizacija | `utils.py` | Unicode NFKC normalizacija + `html.escape()` |
| XSS zaštita | `utils.py` | Svi korisnički unosi sanitizirani prije pohrane i prikaza |
| Audit log | `database.py` | Svaki INSERT/UPDATE/DELETE bilježi se u `audit_log` tablicu |
| DB CHECK constraints | `database.py` | `CHECK(type IN ('Prihod', 'Trošak'))`, `CHECK(amount >= 0)` |
| Connection pool | `database.py` | `psycopg2.pool.ThreadedConnectionPool(2, 10)` |
| Friendly error UI | svugdje | Stack trace nikad nije vidljiv korisniku |

### .env datoteka

```bash
# Generiraj jaku lozinku:
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

Sadržaj `.env`:
```
ACCESS_CODE=tvoja_jaka_lozinka
DB_HOST=localhost
DB_PORT=5432
DB_NAME=waldoslair_db
DB_USER=waldothelazydb
DB_PASS=lozinka_baze

# Opcionalno — email notifikacije pri loginu
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tvoj@gmail.com
SMTP_PASS=app_password_iz_google
NOTIFY_EMAIL=tvoj@gmail.com
```

**NIKAD ne commitas `.env`!** Već je u `.gitignore`.

---

## 🗄️ Baza podataka (PostgreSQL)

### Inicijalni setup (jednom)

```bash
sudo -u postgres psql
```
```sql
CREATE DATABASE waldoslair_db;
CREATE USER waldothelazydb WITH PASSWORD 'tvoja_lozinka';
GRANT ALL PRIVILEGES ON DATABASE waldoslair_db TO waldothelazydb;
GRANT ALL ON SCHEMA public TO waldothelazydb;
ALTER SCHEMA public OWNER TO waldothelazydb;
\q
```

### Tablice (auto-kreirane pri prvom pokretanju)

```
transactions  — financijske transakcije
settings      — konfiguracija (početno stanje, kredit)
audit_log     — automatski log svih izmjena (INSERT/UPDATE/DELETE)
```

### Indeksi

```
idx_tx_account            — brzo dohvaćanje po računu
idx_tx_date               — sortiranje po datumu
idx_audit_table_record    — kompozitni (table_name, record_id)
idx_audit_timestamp       — sortiranje po vremenu
```

### Backup

```bash
# Ručni backup
pg_dump -U waldothelazydb waldoslair_db > backup_$(date +%Y%m%d).sql

# Automatski daily backup — dodaj u crontab:
# crontab -e
# 0 2 * * * pg_dump -U waldothelazydb waldoslair_db | gzip > ~/backups/waldoslair_$(date +\%Y\%m\%d).sql.gz

# Off-site backup s rclone (OneDrive):
# rclone copy ~/backups/ onedrive:waldoslair-backups/
```

---

## 🧩 Finance modul — tabovi

| Tab | Opis |
|---|---|
| 🦇 Tekući Račun | Pregled i uređivanje transakcija tekućeg računa |
| 💳 MasterCard Kreditni | Transakcije s filtrom datumskog raspona |
| 🍪 Keks | Keks štedni račun |
| 🌍 Revolut | Revolut račun |
| 🏖️ Troškovi Njivice | Zajednički troškovi podijeljeni na 3 (s grafom) |
| 🏦 Kredit | Tracker otplate kredita s progress barom |
| 📊 Reporti | Tjedni/mjesečni pregled + CSV export |
| ⚙️ Postavke | Početno stanje Tekućeg računa + postavke kredita |

### Nova transakcija

Gumb **➕ Nova Transakcija** otvara inline formu s:
- Segmented control za Prihod/Trošak
- Pametnim dropdownom (kategorije se mijenjaju ovisno o tipu)
- Automatskim transferom: Trošak kategorije "Keks"/"Revolut" → automatski kreira Prihod na tom računu

### Automatizacija transfera

Kada se na **Tekućem računu** ili **MasterCard Kreditnom** unese trošak s kategorijom `Keks` ili `Revolut`, sustav automatski kreira odgovarajući prihod na tom računu.

---

## 🔧 Dodavanje novog modula u HUB

1. Kreiraj novu Python datoteku, npr. `grocery_ui.py`, s `render()` funkcijom
2. Dodaj u `config.py` → `NAV_PAGES` listu
3. Dodaj handler u `main.py` → `_PAGE_HANDLERS` dict
4. Dodaj `show_grocery()` funkciju u `main.py`
5. Dodaj karticu u `show_home()` u `main.py`

---

## ⚙️ systemd Service (produkcija)

```bash
# Kopiraj service file
sudo cp waldoslair.service /etc/systemd/system/

# Postavi tajne (ne stavljaj u service file direktno!)
sudo systemctl edit waldoslair.service
# Dodaj:
# [Service]
# Environment="ACCESS_CODE=..."
# Environment="DB_PASS=..."

# Aktiviraj
sudo systemctl daemon-reload
sudo systemctl enable waldoslair
sudo systemctl start waldoslair
```

---

## 📦 Tech Stack

| Komponenta | Tehnologija | Verzija |
|---|---|---|
| Frontend + Backend | Streamlit | 1.40.0 |
| Jezik | Python | 3.12 |
| Baza podataka | PostgreSQL | 16 |
| DB adapter | psycopg2-binary | 2.9.9 |
| Data processing | Pandas | 2.2.3 |
| HTTP requests | Requests | 2.32.3 |
| Secrets | python-dotenv | 1.0.1 |
| Hosting | Ubuntu 26.04 LTS / ThinkCentre M93p | — |
| Pristup | Cloudflare Zero Trust (Faza 2) | — |

---

## 🗺️ Roadmap

| Modul | Tema | Status |
|---|---|---|
| 💰 Personal Finance | DC / Batman | ✅ Aktivno |
| 🍲 Meal Planner | Lord of the Rings | 🔧 Under Development |
| 🏋️ Workout Plan | Marvel | 🔧 Under Development |
| 🪵 Woodworking | Dungeons & Dragons | 🔧 Under Development |
| 🛒 Grocery Shopping | Star Wars / Cantina | 🔧 Under Development |
| 📡 Tech Scene News | Star Wars / Galactic Network | 🔧 Under Development |
