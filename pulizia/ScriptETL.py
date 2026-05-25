import pandas as pd
import numpy as np
from datetime import datetime
from decimal import Decimal
import os

# -----------------------------
# Percorsi base
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PATH_STAZIONI    = os.path.join(BASE_DIR, "..", "data", "raw", "stazioniqaria.csv")
PATH_MISURAZIONI = os.path.join(BASE_DIR, "..", "data", "raw", "dataset_originale.csv")

# Cartelle output
OUT_PB = os.path.join(BASE_DIR, "..", "data", "powerbi")
OUT_MY = os.path.join(BASE_DIR, "..", "data", "mysql")
os.makedirs(OUT_PB, exist_ok=True)
os.makedirs(OUT_MY, exist_ok=True)

# Output Power BI
OUT_STAZIONI_PB        = os.path.join(OUT_PB, "stazioni_powerbi.csv")
OUT_INQUINANTI_PB      = os.path.join(OUT_PB, "inquinanti_powerbi.csv")
OUT_STAZIONI_INQ_PB    = os.path.join(OUT_PB, "stazioni_inquinanti_powerbi.csv")
OUT_MISURAZIONI_PB     = os.path.join(OUT_PB, "misurazioni_powerbi.csv")

# Output MySQL
OUT_STAZIONI_MY        = os.path.join(OUT_MY, "stazioni_mysql.csv")
OUT_INQUINANTI_MY      = os.path.join(OUT_MY, "inquinanti_mysql.csv")
OUT_STAZIONI_INQ_MY    = os.path.join(OUT_MY, "stazioni_inquinanti_mysql.csv")
OUT_MISURAZIONI_MY     = os.path.join(OUT_MY, "misurazioni_mysql.csv")


# -----------------------------
# Funzioni utili
# -----------------------------
def to_italian_number(value):
    if pd.isna(value) or value == "":
        return ""
    if isinstance(value, (Decimal, float, int)):
        value = f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value).replace(".", ",")


def to_mysql_number(value):
    if pd.isna(value) or value == "":
        return None
    return str(value).replace(",", ".")


def parse_date(value):
    if pd.isna(value) or value == "":
        return ""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def clean_for_mysql(df):
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df = df.replace("", np.nan)
    return df


# -----------------------------
# ETL STAZIONI + INQUINANTI + STAZIONI_INQUINANTI
# -----------------------------
def etl_stazioni():
    print(">>> Pulizia STAZIONI...")

    df = pd.read_csv(PATH_STAZIONI, sep=";")

    if "Location" in df.columns:
        df = df.drop(columns=["Location"])

    df["inizio_operativita"] = df["inizio_operativita"].apply(parse_date)
    df["fine_operativita"]   = df["fine_operativita"].apply(parse_date)

    # POWER BI
    df_pb = df.copy()
    df_pb["LONG_X_4326"] = df_pb["LONG_X_4326"].astype(str).str.replace(".", ",")
    df_pb["LAT_Y_4326"]  = df_pb["LAT_Y_4326"].astype(str).str.replace(".", ",")
    df_pb.rename(columns={"LONG_X_4326": "Longitudine", "LAT_Y_4326": "Latitudine"}, inplace=True)
    df_pb.to_csv(OUT_STAZIONI_PB, sep=";", index=False, encoding="utf-8-sig")

    # MYSQL
    df_my = df.copy()
    if "inquinanti" in df_my.columns:
        df_my = df_my.drop(columns=["inquinanti"])
    df_my["LONG_X_4326"] = df_my["LONG_X_4326"].astype(str).str.replace(",", ".")
    df_my["LAT_Y_4326"]  = df_my["LAT_Y_4326"].astype(str).str.replace(",", ".")
    df_my.rename(columns={"LONG_X_4326": "longitudine", "LAT_Y_4326": "latitudine"}, inplace=True)
    df_my = clean_for_mysql(df_my)
    df_my.to_csv(OUT_STAZIONI_MY, sep=";", index=False, encoding="utf-8")

    # -----------------------------
    # INQUINANTI
    # -----------------------------
    print(">>> Pulizia INQUINANTI...")

    inq_set = set()
    for raw in df["inquinanti"]:
        if pd.isna(raw):
            continue
        for p in str(raw).split(","):
            nome = p.strip()
            if nome:
                inq_set.add(nome)

    df_inq = pd.DataFrame(sorted(list(inq_set)), columns=["nome"])
    df_inq.insert(0, "id_inquinante", range(1, len(df_inq) + 1))

    df_inq.to_csv(OUT_INQUINANTI_PB, sep=";", index=False, encoding="utf-8-sig")
    df_inq.to_csv(OUT_INQUINANTI_MY, sep=";", index=False, encoding="utf-8")

    map_inq = {row["nome"]: row["id_inquinante"] for _, row in df_inq.iterrows()}

    # -----------------------------
    # STAZIONI_INQUINANTI
    # -----------------------------
    print(">>> Pulizia STAZIONI_INQUINANTI...")

    rows = []
    for _, row in df.iterrows():
        id_amat = int(row["id_amat"])
        raw = row["inquinanti"]
        if pd.isna(raw):
            continue
        visti = set()
        for p in str(raw).split(","):
            nome = p.strip()
            if nome and nome not in visti:
                visti.add(nome)
                rows.append([id_amat, map_inq[nome]])

    df_si = pd.DataFrame(rows, columns=["id_amat", "id_inquinante"])

    df_si.to_csv(OUT_STAZIONI_INQ_PB, sep=";", index=False, encoding="utf-8-sig")
    df_si.to_csv(OUT_STAZIONI_INQ_MY, sep=";", index=False, encoding="utf-8")

    print(">>> STAZIONI + INQUINANTI completati.\n")


# -----------------------------
# ETL MISURAZIONI
# -----------------------------
def etl_misurazioni():
    print(">>> Pulizia MISURAZIONI...")

    df = pd.read_csv(PATH_MISURAZIONI, sep=";")
    df["data"] = df["data"].apply(parse_date)

    df_inq  = pd.read_csv(OUT_INQUINANTI_PB, sep=";")
    map_inq = {row["nome"]: row["id_inquinante"] for _, row in df_inq.iterrows()}

    df["inquinante_id"] = df["inquinante"].apply(lambda x: map_inq.get(str(x).strip(), ""))

    # POWER BI
    df_pb     = df.copy()
    df_pb["valore"] = df_pb["valore"].apply(to_italian_number)
    df_pb_out = df_pb[["stazione_id", "data", "inquinante_id", "valore"]]
    df_pb_out.to_csv(OUT_MISURAZIONI_PB, sep=";", index=False, encoding="utf-8-sig")

    # MYSQL
    df_my     = df.copy()
    df_my["valore"] = df_my["valore"].apply(to_mysql_number)
    df_my     = clean_for_mysql(df_my)
    df_my_out = df_my[["stazione_id", "data", "inquinante_id", "valore"]]
    df_my_out.to_csv(OUT_MISURAZIONI_MY, sep=";", index=False, encoding="utf-8")

    print(">>> MISURAZIONI completato.\n")


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    etl_stazioni()
    etl_misurazioni()
    print("✅ CSV Power BI + MySQL generati con successo!")