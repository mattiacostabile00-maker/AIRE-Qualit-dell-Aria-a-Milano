"""
app/views.py
─────────────────────────────────────────────────────────────
Tutti i pannelli (Frame) dell'interfaccia Tkinter.

Pannelli disponibili:
  - PannelloDati   : tabella dati dal DB con filtri
  - PannelloGrafici: grafici trend inquinanti
  - PannelloAI     : risultati ML + previsione in tempo reale
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

import app.db    as db
import app.utils as utils


# ════════════════════════════════════════════════════════════
# PANNELLO 1 — DATI
# ════════════════════════════════════════════════════════════

class PannelloDati(tk.Frame):
    """
    Mostra i dati della tabella rilevamenti con filtri
    per inquinante e stazione.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#f5f7fa", **kwargs)
        self._build_ui()
        self.carica_dati()

    def _build_ui(self):
        # ── Barra filtri ──────────────────────────────────
        bar = tk.Frame(self, bg="#1a3a5c", pady=6)
        bar.pack(fill="x")

        tk.Label(bar, text="Inquinante:", bg="#1a3a5c", fg="white",
                 font=("Arial", 10)).pack(side="left", padx=(12, 4))
        self.var_inq = tk.StringVar(value="Tutti")
        inq_opts = ["Tutti", "PM10", "PM25", "NO2", "O3", "C6H6", "CO_8h", "SO2"]
        ttk.Combobox(bar, textvariable=self.var_inq, values=inq_opts,
                     width=10, state="readonly").pack(side="left", padx=4)

        tk.Label(bar, text="Stazione:", bg="#1a3a5c", fg="white",
                 font=("Arial", 10)).pack(side="left", padx=(12, 4))
        self.var_sta = tk.StringVar(value="Tutte")
        sta_opts = ["Tutte", "2", "3", "4", "6", "7"]
        ttk.Combobox(bar, textvariable=self.var_sta, values=sta_opts,
                     width=8, state="readonly").pack(side="left", padx=4)

        tk.Button(bar, text="🔍 Filtra", command=self.carica_dati,
                  bg="#2ecc71", fg="white", relief="flat",
                  font=("Arial", 10, "bold"), padx=10).pack(side="left", padx=12)

        self.lbl_count = tk.Label(bar, text="", bg="#1a3a5c",
                                  fg="#aad4f5", font=("Arial", 9))
        self.lbl_count.pack(side="right", padx=12)

        # ── Tabella ───────────────────────────────────────
        cols = ("ID", "Stazione", "Data", "Inquinante", "Valore")
        self.tree = ttk.Treeview(self, columns=cols, show="headings",
                                  selectmode="browse")
        for col in cols:
            self.tree.heading(col, text=col)
        self.tree.column("ID",         width=50,  anchor="center")
        self.tree.column("Stazione",   width=80,  anchor="center")
        self.tree.column("Data",       width=120, anchor="center")
        self.tree.column("Inquinante", width=100, anchor="center")
        self.tree.column("Valore",     width=100, anchor="center")

        scroll = ttk.Scrollbar(self, orient="vertical",
                               command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True, pady=8, padx=8)
        scroll.pack(side="right", fill="y", pady=8)

    def carica_dati(self):
        """Esegue la query con i filtri scelti."""
        inq = self.var_inq.get()
        sta = self.var_sta.get()

        sql    = "SELECT id, stazione_id, data, inquinante, valore FROM rilevamenti WHERE 1=1"
        params = []
        if inq != "Tutti":
            sql += " AND inquinante = %s"
            params.append(inq)
        if sta != "Tutte":
            sql += " AND stazione_id = %s"
            params.append(int(sta))
        sql += " ORDER BY data DESC LIMIT 500"

        try:
            df = db.query_df(sql, params=tuple(params) if params else None)
            self.tree.delete(*self.tree.get_children())
            for _, row in df.iterrows():
                val = f"{row['valore']:.1f}" if pd.notna(row["valore"]) else "—"
                self.tree.insert("", "end",
                    values=(row["id"], row["stazione_id"],
                            row["data"], row["inquinante"], val))
            self.lbl_count.config(text=f"{len(df)} righe mostrate")
        except Exception as e:
            messagebox.showerror("Errore DB", str(e))


# ════════════════════════════════════════════════════════════
# PANNELLO 2 — GRAFICI
# ════════════════════════════════════════════════════════════

class PannelloGrafici(tk.Frame):
    """
    Mostra il trend temporale di un inquinante per stazione.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#f5f7fa", **kwargs)
        self._build_ui()

    def _build_ui(self):
        # ── Barra controlli ───────────────────────────────
        bar = tk.Frame(self, bg="#1a3a5c", pady=6)
        bar.pack(fill="x")

        tk.Label(bar, text="Inquinante:", bg="#1a3a5c", fg="white",
                 font=("Arial", 10)).pack(side="left", padx=(12, 4))
        self.var_inq = tk.StringVar(value="PM10")
        ttk.Combobox(bar, textvariable=self.var_inq,
                     values=["PM10","PM25","NO2","O3","C6H6","SO2","CO_8h"],
                     width=8, state="readonly").pack(side="left", padx=4)

        tk.Button(bar, text="📈 Aggiorna Grafico", command=self.aggiorna,
                  bg="#2ecc71", fg="white", relief="flat",
                  font=("Arial", 10, "bold"), padx=10).pack(side="left", padx=12)

        # ── Area grafico ──────────────────────────────────
        self.fig, self.ax = plt.subplots(figsize=(9, 4), dpi=90)
        self.fig.patch.set_facecolor("#f5f7fa")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True,
                                          padx=10, pady=10)
        self.aggiorna()

    def aggiorna(self):
        inq = self.var_inq.get()
        try:
            df = db.query_df(
                "SELECT data, stazione_id, valore FROM rilevamenti "
                "WHERE inquinante = %s AND valore IS NOT NULL "
                "ORDER BY data",
                params=(inq,)
            )
            df["data"] = pd.to_datetime(df["data"])
            self.ax.clear()
            for sta in sorted(df["stazione_id"].unique()):
                sub = df[df["stazione_id"] == sta]
                self.ax.plot(sub["data"], sub["valore"],
                             label=f"Stazione {sta}", linewidth=1.4, alpha=0.85)
            self.ax.set_title(f"Trend {inq} per stazione — 2025",
                              fontsize=13, pad=10)
            self.ax.set_xlabel("Data")
            self.ax.set_ylabel(f"{inq} (µg/m³)")
            self.ax.legend(fontsize=9)
            self.ax.grid(alpha=0.3)
            self.fig.tight_layout()
            self.canvas.draw()
        except Exception as e:
            messagebox.showerror("Errore grafico", str(e))


# ════════════════════════════════════════════════════════════
# PANNELLO 3 — AI / MACHINE LEARNING
# ════════════════════════════════════════════════════════════

class PannelloAI(tk.Frame):
    """
    Pannello AI: mostra le metriche dei modelli ML
    e permette previsioni in tempo reale.

    I modelli vengono addestrati in background al primo caricamento
    per non bloccare l'interfaccia.
    """

    COLORI_QUALITA = {
        "buona":   "#27ae60",
        "media":   "#f39c12",
        "cattiva": "#e74c3c",
    }
    EMOJI_QUALITA = {
        "buona": "🟢", "media": "🟡", "cattiva": "🔴"
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#f5f7fa", **kwargs)
        self._risultati = None      # dizionario di addestra_modelli()
        self._build_ui()
        self._addestra_async()      # training in thread separato

    # ── Costruzione UI ───────────────────────────────────

    def _build_ui(self):
        # Titolo
        tk.Label(self, text="🤖  Pannello AI — Qualità dell'Aria",
                 font=("Arial", 14, "bold"), bg="#1a3a5c", fg="white",
                 pady=10).pack(fill="x")

        # Stato training
        self.lbl_stato = tk.Label(self,
            text="⏳ Addestramento modelli in corso...",
            font=("Arial", 10), bg="#f5f7fa", fg="#888")
        self.lbl_stato.pack(pady=(10, 0))

        # Frame metriche
        self.frame_metriche = tk.LabelFrame(self, text="📊 Prestazioni modelli",
            font=("Arial", 10, "bold"), bg="#f5f7fa", padx=12, pady=8)
        self.frame_metriche.pack(fill="x", padx=16, pady=10)

        self.lbl_reg = tk.Label(self.frame_metriche, text="—",
            bg="#f5f7fa", font=("Arial", 10))
        self.lbl_reg.pack(anchor="w")

        self.lbl_rf = tk.Label(self.frame_metriche, text="—",
            bg="#f5f7fa", font=("Arial", 10))
        self.lbl_rf.pack(anchor="w")

        self.lbl_knn = tk.Label(self.frame_metriche, text="—",
            bg="#f5f7fa", font=("Arial", 10))
        self.lbl_knn.pack(anchor="w")

        # Frame previsione
        frame_prev = tk.LabelFrame(self, text="🔍 Previsione in tempo reale",
            font=("Arial", 10, "bold"), bg="#f5f7fa", padx=12, pady=8)
        frame_prev.pack(fill="x", padx=16, pady=4)

        self._entries = {}
        defaults = {"no2": "55", "pm25": "28", "c6h6": "1.5", "o3": "20"}
        labels   = {"no2": "NO₂", "pm25": "PM2.5", "c6h6": "C₆H₆", "o3": "O₃"}

        for feat, default in defaults.items():
            row = tk.Frame(frame_prev, bg="#f5f7fa")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{labels[feat]}:",
                     width=8, anchor="w", bg="#f5f7fa",
                     font=("Arial", 10)).pack(side="left")
            ent = tk.Entry(row, width=10, font=("Arial", 10))
            ent.insert(0, default)
            ent.pack(side="left", padx=4)
            tk.Label(row, text="µg/m³", bg="#f5f7fa",
                     font=("Arial", 9), fg="gray").pack(side="left")
            self._entries[feat] = ent

        tk.Button(self, text="🔮  Prevedi Qualità Aria",
                  command=self._esegui_previsione,
                  bg="#1a3a5c", fg="white", relief="flat",
                  font=("Arial", 11, "bold"), pady=7,
                  cursor="hand2").pack(padx=16, pady=10, fill="x")

        # Risultato previsione
        self.lbl_risultato = tk.Label(self,
            text="Inserisci i valori e clicca Prevedi",
            font=("Arial", 12), bg="#f5f7fa", fg="#777")
        self.lbl_risultato.pack(pady=4)

        self.lbl_pm10 = tk.Label(self, text="",
            font=("Arial", 10), bg="#f5f7fa", fg="#444")
        self.lbl_pm10.pack()

        self.lbl_prob = tk.Label(self, text="",
            font=("Arial", 9), bg="#f5f7fa", fg="#666")
        self.lbl_prob.pack(pady=(2, 12))

    # ── Training asincrono ────────────────────────────────

    def _addestra_async(self):
        """Addestra i modelli in background per non bloccare la GUI."""
        def _lavoro():
            try:
                self._risultati = utils.addestra_modelli()
                self.after(0, self._aggiorna_metriche)
            except Exception as e:
                self.after(0, lambda err=e: self.lbl_stato.config(
                    text=f"❌ Errore training: {err}", fg="red"))

        t = threading.Thread(target=_lavoro, daemon=True)
        t.start()

    def _aggiorna_metriche(self):
        """Aggiorna i label con le metriche calcolate (chiamata dal thread UI)."""
        m = self._risultati["metriche"]
        self.lbl_stato.config(text="✅ Modelli pronti!", fg="#27ae60")

        self.lbl_reg.config(
            text=f"📈 Regressione Lineare  →  R² = {m['r2']}  |  RMSE = {m['rmse']} µg/m³")
        self.lbl_rf.config(
            text=f"🌲 Random Forest        →  Accuratezza = {m['acc_rf']*100:.1f}%",
            fg="#27ae60" if m["acc_rf"] >= 0.75 else "#f39c12")
        self.lbl_knn.config(
            text=f"🔵 KNN (k=5)            →  Accuratezza = {m['acc_knn']*100:.1f}%")

    # ── Previsione ────────────────────────────────────────

    def _esegui_previsione(self):
        if self._risultati is None:
            messagebox.showinfo("Attendi",
                "I modelli sono ancora in fase di addestramento.")
            return
        try:
            valori = {f: float(self._entries[f].get())
                      for f in utils.FEATURE_COLS}
        except ValueError:
            messagebox.showerror("Errore", "Inserisci valori numerici validi.")
            return

        res     = utils.prevedi(valori, self._risultati)
        qualita = res["qualita"]
        colore  = self.COLORI_QUALITA[qualita]
        emoji   = self.EMOJI_QUALITA[qualita]
        prob    = res["probabilita"]

        self.lbl_risultato.config(
            text=f"{emoji}  Qualità prevista: {qualita.upper()}",
            fg=colore, font=("Arial", 14, "bold"))

        self.lbl_pm10.config(
            text=f"PM10 stimato: {res['pm10_stima']} µg/m³")

        self.lbl_prob.config(
            text=f"Probabilità → buona: {prob.get('buona',0)*100:.0f}%  "
                 f"media: {prob.get('media',0)*100:.0f}%  "
                 f"cattiva: {prob.get('cattiva',0)*100:.0f}%")
