"""
app/utils.py
─────────────────────────────────────────────────────────────
Funzioni di utilità per analisi dati e Machine Learning.

Dipende da app/db.py per caricare i dati dal DB.
Espone:
  - classifica_qualita(pm10)  → etichetta testuale
  - get_df_wide()             → DataFrame in formato largo
  - prepara_dati_ml()         → (df_ml, feature_cols)
  - addestra_modelli()        → dizionario con tutti i modelli + metriche
  - prevedi(valori_dict)      → previsione qualità aria su nuovo campione
"""
import sys
import os
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    r2_score, mean_squared_error,
    accuracy_score, classification_report, confusion_matrix
)

import app.db as db


# ── Feature usate dai modelli ──────────────────────────────
FEATURE_COLS = ["no2", "pm25", "c6h6", "o3"]

# ── Soglie qualità aria (µg/m³) ────────────────────────────
SOGLIA_BUONA   = 25    # PM10 ≤ 25 → buona
SOGLIA_MEDIA   = 50    # PM10 26-50 → media
                       # PM10 > 50  → cattiva


# ── 1. Classificazione qualità ─────────────────────────────

def classifica_qualita(pm10) -> str | None:
    """
    Converte un valore numerico di PM10 in un'etichetta qualitativa.

    Soglie (µg/m³):
        ≤ 25       → 'buona'
        26 a 50    → 'media'
        > 50       → 'cattiva'
        NaN/None   → None

    Esempio:
        classifica_qualita(38)   # → 'media'
        classifica_qualita(12)   # → 'buona'
        classifica_qualita(75)   # → 'cattiva'
    """
    if pd.isna(pm10):
        return None
    elif pm10 <= SOGLIA_BUONA:
        return "buona"
    elif pm10 <= SOGLIA_MEDIA:
        return "media"
    else:
        return "cattiva"


# ── 2. Carica dati in formato largo ───────────────────────

def get_df_wide() -> pd.DataFrame:
    """
    Carica i dati dalla vista v_wide del DB e restituisce
    un DataFrame con una riga per ogni (data, stazione).
    Aggiunge la colonna 'qualita' basata su PM10.

    Colonne risultanti:
        data | stazione_id | pm10 | pm25 | no2 | o3 | c6h6 | co_8h | so2 | qualita

    Esempio:
        df = utils.get_df_wide()
        print(df.head())
    """
    df = db.query_df("SELECT * FROM v_wide ORDER BY data, stazione_id")
    df["qualita"] = df["pm10"].apply(classifica_qualita)
    return df


# ── 3. Prepara dataset per ML ─────────────────────────────

def prepara_dati_ml() -> tuple[pd.DataFrame, list[str]]:
    """
    Carica i dati, filtra le righe senza PM10 e imputa
    i valori mancanti delle feature con la media di colonna.

    Restituisce:
        (df_ml, feature_cols)
        - df_ml       : DataFrame pronto per il training
        - feature_cols: lista dei nomi delle feature usate

    Esempio:
        df_ml, feats = utils.prepara_dati_ml()
        print(f"Dataset ML: {len(df_ml)} righe")
    """
    df = get_df_wide()

    # Tieni solo righe con PM10 (target della regressione)
    df_ml = df.dropna(subset=["pm10"]).copy()

    # Imputa i mancanti nelle feature con la media
    for col in FEATURE_COLS:
        df_ml[col] = df_ml[col].fillna(df_ml[col].mean())

    return df_ml, FEATURE_COLS


# ── 4. Addestra tutti i modelli ───────────────────────────

def addestra_modelli() -> dict:
    """
    Addestra Regressione Lineare, Random Forest e KNN
    sul dataset recuperato dal database.

    Restituisce un dizionario con:
        {
          "modelli": {regressione, rf, knn, scaler, le},
          "metriche": {r2, rmse, acc_rf, acc_knn},
          "dati":     {X_test_r, y_test_r, X_test_c, y_test_c, le}
        }

    Esempio:
        risultati = utils.addestra_modelli()
        print("R²:", risultati["metriche"]["r2"])
        print("Accuratezza RF:", risultati["metriche"]["acc_rf"])
    """
    df_ml, feats = prepara_dati_ml()

    # ── Regressione Lineare (target: valore numerico PM10) ──
    X_reg = df_ml[feats]
    y_reg = df_ml["pm10"]

    X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(
        X_reg, y_reg, test_size=0.2, random_state=42
    )
    model_lr = LinearRegression()
    model_lr.fit(X_train_r, y_train_r)

    y_pred_r = model_lr.predict(X_test_r)
    r2   = r2_score(y_test_r, y_pred_r)
    rmse = np.sqrt(mean_squared_error(y_test_r, y_pred_r))

    # ── Classificazione (target: qualita buona/media/cattiva) ──
    df_clf = df_ml.dropna(subset=["qualita"]).copy()
    le     = LabelEncoder()
    df_clf["qualita_num"] = le.fit_transform(df_clf["qualita"])

    X_clf = df_clf[feats]
    y_clf = df_clf["qualita_num"]

    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X_clf, y_clf, test_size=0.2, random_state=42, stratify=y_clf
    )

    # Random Forest
    model_rf = RandomForestClassifier(n_estimators=100, random_state=42)
    model_rf.fit(X_train_c, y_train_c)
    acc_rf = accuracy_score(y_test_c, model_rf.predict(X_test_c))

    # KNN (richiede normalizzazione!)
    scaler     = StandardScaler()
    X_train_k  = scaler.fit_transform(X_train_c)
    X_test_k   = scaler.transform(X_test_c)
    model_knn  = KNeighborsClassifier(n_neighbors=5)
    model_knn.fit(X_train_k, y_train_c)
    acc_knn = accuracy_score(y_test_c, model_knn.predict(X_test_k))

    return {
        "modelli": {
            "regressione": model_lr,
            "rf":          model_rf,
            "knn":         model_knn,
            "scaler":      scaler,
            "le":          le,
        },
        "metriche": {
            "r2":      round(r2,      3),
            "rmse":    round(rmse,    2),
            "acc_rf":  round(acc_rf,  3),
            "acc_knn": round(acc_knn, 3),
        },
        "dati": {
            "X_test_r": X_test_r,
            "y_test_r": y_test_r,
            "X_test_c": X_test_c,
            "y_test_c": y_test_c,
        }
    }


# ── 5. Previsione su nuovo campione ───────────────────────

def prevedi(valori: dict, risultati: dict) -> dict:
    """
    Esegue una previsione su un nuovo campione di dati.

    Parametri:
        valori    : dizionario {no2, pm25, c6h6, o3}
        risultati : output di addestra_modelli()

    Restituisce:
        {
          "qualita"    : str  (es. "media")
          "probabilita": dict (es. {"buona": 0.1, "media": 0.7, "cattiva": 0.2})
          "pm10_stima" : float
        }

    Esempio:
        result = utils.prevedi(
            {"no2": 55, "pm25": 28, "c6h6": 1.5, "o3": 20},
            risultati
        )
        print(result["qualita"])  # → "media"
    """
    modelli = risultati["modelli"]
    le      = modelli["le"]
    scaler  = modelli["scaler"]

    # Crea DataFrame con i valori nell'ordine corretto
    X_new = pd.DataFrame([[valori[f] for f in FEATURE_COLS]], columns=FEATURE_COLS)

    # Stima PM10 (regressione)
    pm10_stima = float(modelli["regressione"].predict(X_new)[0])

    # Classificazione qualità (Random Forest)
    pred_num  = modelli["rf"].predict(X_new)[0]
    pred_prob = modelli["rf"].predict_proba(X_new)[0]
    qualita   = le.inverse_transform([pred_num])[0]
    proba_dict = {cls: round(float(p), 3) for cls, p in zip(le.classes_, pred_prob)}

    return {
        "qualita":     qualita,
        "probabilita": proba_dict,
        "pm10_stima":  round(pm10_stima, 1),
    }
