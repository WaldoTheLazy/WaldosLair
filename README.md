# 🏰 WaldosLair

> *"A long time ago in a galaxy far, far away... a Waldo The Lazy needed a central hub."*

Osobni HUB za upravljanje svakodnevnim životom. Aktivni modul: **Personal Finance (Wayne Enterprises)**.

---

## 📁 Struktura projekta

```
waldoslair_app/
├── main.py                    # Entry point — streamlit run main.py
│
├── core/
│   ├── config.py              # Sve konstante + .env učitavanje
│   ├── db.py                  # PostgreSQL CRUD, audit log, connection pool, cache
│   └── utils.py               # Valuta, sanitizacija, citati, email notifikacije
│
├── ui/
│   ├── styles.py              # Sav CSS (Dark Star + Wayne Enterprises teme)
│   ├── app.py                 # Routing, auth, navigacija, sve stranice
│   └── pages/
│       └── finance.py         # Finance modul (Wayne Enterprises tema)
│
├── tools/
│   └── migrate_sqlite_to_pg.py  # Jednokratna migracija SQLite → PostgreSQL
│
├── logs/                      # app.log (auto-kreiran, NIJE u gitu)
├── tests/                     # Testovi (TODO)
│
├── .env.example               # Template za .env
├── .gitignore
├── requirements.txt
└── waldoslair.service         # systemd service file
```

---

## 🚀 Pokretanje

### 1. PostgreSQL setup (jednom na serveru)

```bash
sudo -u postgres psql
CREATE DATABASE waldoslair_db;
CREATE USER waldothelazydb WITH PASSWORD 'tvoja_jaka_lozinka_baze';
GRANT ALL PRIVILEGES ON DATABASE waldoslair_db TO waldothelazydb;
GRANT ALL ON SCHEMA public TO waldothelazydb;
\q
```

### 2. Lokalni razvoj

```bash
git clone git@github.com:tvoj-user/waldoslair.git waldoslair_app
cd waldoslair_app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env           # postavi ACCESS_CODE, DB_PASS, (opcionalno email)
streamlit run main.py
```

### 3. Migracija starih SQLite podataka (jednokratno)

```bash
# Kopiraj staru finance.db u root direktorij, pa pokreni:
python tools/migrate_sqlite_to_pg.py --sqlite finance.db
```

### 4. Produkcija (ThinkCentre)

```bash
ssh -p 2222 waldothelazy@waldoslair
cd ~/waldoslair_app && git pull
pip install -r requirements.txt

# Postavi secrets (samo jednom / pri promjeni):
sudo systemctl edit waldoslair.service
# Dodaj:
# [Service]
# Environment="ACCESS_CODE=..."
# Environment="DB_PASS=..."

sudo cp waldoslair.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable waldoslair
sudo systemctl start waldoslair
```

---

## 🔐 Sigurnost

| Mjera | Gdje | Opis |
|---|---|---|
| `.env` za tajne | `core/config.py` | `ACCESS_CODE`, `DB_PASS` nikad hardkodirani |
| Timing-safe auth | `ui/app.py` | `hmac.compare_digest()` |
| Rate limiting | `ui/app.py` | Max 10 neuspješnih pokušaja |
| Login email alert | `core/utils.py` | `send_login_notification()` |
| SQL parametrizacija | `core/db.py` | Svi upiti koriste `%s` placeholdere |
| Whitelist UPDATE kolumni | `core/db.py` | `_ALLOWED_UPDATE_COLUMNS` frozenset |
| Input sanitizacija | `core/utils.py` | Unicode NFKC + `html.escape()` |
| Audit log | `core/db.py` | Svaki INSERT/UPDATE/DELETE logiran |
| Connection pool | `core/db.py` | `ThreadedConnectionPool(2, 10)` |
| `@st.cache_data` | `core/db.py` | TTL=300s na READ funkcijama |
| Friendly error UI | svugdje | Stack trace nikad nije vidljiv korisniku |

---

## 🗄️ Baza podataka

```sql
-- Tablice:
transactions   -- financijske transakcije
settings       -- konfiguracija (početno stanje, kredit)
audit_log      -- automatski log svih izmjena

-- Indeksi (per specifikacija):
idx_tx_account, idx_tx_date
idx_audit_table_record, idx_audit_timestamp
```

### Backup

```bash
# Lokalni backup (dodaj u crontab):
# 0 2 * * * pg_dump -U waldothelazydb waldoslair_db | gzip > ~/backups/waldoslair_$(date +\%Y\%m\%d).sql.gz

# Off-site s rclone (OneDrive):
# rclone copy ~/backups/ onedrive:waldoslair-backups/
```

---

## 🔧 Dodavanje novog modula

1. Kreiraj `ui/pages/novi_modul.py` s `render()` funkcijom
2. Dodaj u `core/config.py` → `NAV_PAGES`
3. Dodaj handler u `ui/app.py` → `_PAGE_HANDLERS` i odgovarajuću `show_*()` funkciju
4. Dodaj karticu u `show_home()` u `ui/app.py`

---

## 📦 Tech Stack

| Komponenta | Tehnologija |
|---|---|
| Frontend + Backend | Python 3.12+ / Streamlit 1.40 |
| Baza podataka | PostgreSQL 16 |
| Caching | `@st.cache_data` (TTL=300s) |
| Data processing | Pandas 2.2 |
| Secrets | python-dotenv |
| Hosting | Ubuntu 26.04 LTS / systemd / Cloudflare Zero Trust |
