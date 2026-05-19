"""
import sys
import os
from pathlib import Path
# Questo risolve i problemi di import ovunque ti trovi nel terminale
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import pandas as pd
from dotenv import load_dotenv

# Carica il .env in modo sicuro cercando la cartella corretta
env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
app/db.py
─────────────────────────────────────────────────────────────
Modulo di connessione al database Supabase (PostgreSQL).

Legge le credenziali dal file .env nella root del progetto.
Espone:
  - get_connection()  → connessione psycopg2 grezza
  - get_engine()      → engine SQLAlchemy (per pandas)
  - query_df(sql)     → esegue una SELECT e restituisce DataFrame
  - esegui(sql)       → esegue INSERT/UPDATE/DELETE
  - carica_csv(path)  → carica dataset_originale.csv nel DB
"""

import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

# Carica le variabili dal file .env
load_dotenv()


# ── Connessione grezza psycopg2 ────────────────────────────

def get_connection():
    """
    Restituisce una connessione psycopg2 al database.
    Ricordati di chiuderla con conn.close() quando hai finito.

    Esempio:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM rilevamenti")
        print(cur.fetchone())
        conn.close()
    """
    return psycopg2.connect(
        host     = os.getenv("DB_HOST"),
        database = os.getenv("DB_NAME", "postgres"),
        user     = os.getenv("DB_USER", "postgres"),
        password = os.getenv("DB_PASSWORD"),
        port     = int(os.getenv("DB_PORT", 5432))
    )


# ── Engine SQLAlchemy (necessario per pandas to_sql) ──────

def get_engine():
    """
    Restituisce un engine SQLAlchemy.
    Usato principalmente da pandas .to_sql() e .read_sql().

    Esempio:
        engine = db.get_engine()
        df.to_sql("rilevamenti", engine, if_exists="append", index=False)
    """
    from sqlalchemy import create_engine
    host     = os.getenv("DB_HOST")
    password = os.getenv("DB_PASSWORD")
    user     = os.getenv("DB_USER", "postgres")
    dbname   = os.getenv("DB_NAME", "postgres")
    port     = os.getenv("DB_PORT", 5432)
    url      = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


# ── Funzioni di utilità ────────────────────────────────────

def query_df(sql: str, params=None) -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)
    """
    Esegue una query SELECT e restituisce un DataFrame pandas.
    La connessione viene aperta e chiusa automaticamente.

    Parametri:
        sql    : stringa SQL con eventuale %s per i parametri
        params : tupla di valori per i placeholder %s

    Esempio:
        df = db.query_df(
            "SELECT * FROM rilevamenti WHERE inquinante = %s",
            params=("PM10",)
        )
    """
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


def esegui(sql: str, params=None):
    """
    Esegue una query di modifica (INSERT, UPDATE, DELETE, CREATE).
    Fa il commit automaticamente.

    Esempio:
        db.esegui(
            "UPDATE rilevamenti SET valore = %s WHERE id = %s",
            params=(42.0, 1)
        )
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def carica_csv(csv_path: str = "data/dataset_originale.csv"):
    print(f"📂 Leggo {csv_path}...")
    df = pd.read_csv(csv_path, sep=";")
    df["data"] = pd.to_datetime(df["data"]).dt.date

    conn = get_connection()
    try:
        cur = conn.cursor()
        inserite = 0
        for _, row in df.iterrows():
            cur.execute("""
                INSERT INTO rilevamenti (stazione_id, data, inquinante, valore)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (stazione_id, data, inquinante) DO NOTHING
            """, (row["stazione_id"], row["data"], row["inquinante"],
                  None if pd.isna(row["valore"]) else row["valore"]))
            inserite += cur.rowcount
        conn.commit()
        print(f"✅ {inserite} righe inserite (duplicate ignorate)!")
    finally:
        conn.close()

# ── Test rapido (esegui con: python app/db.py) ─────────────

if __name__ == "__main__":
    print("🔌 Avvio caricamento forzato del dataset...")
    try:
        # Inseriamo direttamente il percorso relativo corretto per quando sei dentro 'app' o fuori
        path_esterno = os.path.join("data", "qaria_datoariagiornostazione_2026-01-28.csv")
        path_interno = os.path.join("..", "data", "qaria_datoariagiornostazione_2026-01-28.csv")
        
        csv_scelto = path_esterno if os.path.exists(path_esterno) else path_interno
        carica_csv(csv_scelto)
    except Exception as e:
        print(f"❌ Errore durante il caricamento: {e}")