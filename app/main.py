"""
app/main.py
─────────────────────────────────────────────────────────────
Entry point dell'applicazione AIRE.

Avvia la finestra Tkinter con tre schede:
  1. Dati      → tabella rilevamenti con filtri
  2. Grafici   → trend temporale degli inquinanti
  3. Pannello AI → metriche ML + previsione in tempo reale

Uso:
    python app/main.py          (dalla root del progetto)
"""

import tkinter as tk
from tkinter import ttk, messagebox

from app.views import PannelloDati, PannelloGrafici, PannelloAI
import app.db as db


class AppAIRE(tk.Tk):
    """Finestra principale dell'applicazione AIRE."""

    def __init__(self):
        super().__init__()
        self.title("AIRE — Qualità dell'Aria a Milano")
        self.geometry("980x680")
        self.configure(bg="#1a3a5c")
        self.resizable(True, True)

        self._build_header()
        self._build_tabs()
        self._verifica_connessione()

    def _build_header(self):
        """Barra superiore con titolo e indicatore connessione."""
        header = tk.Frame(self, bg="#1a3a5c", pady=10)
        header.pack(fill="x")

        tk.Label(header,
            text="🌿  AIRE — Analisi Inquinamento Milano 2025",
            font=("Arial", 16, "bold"), bg="#1a3a5c", fg="white"
        ).pack(side="left", padx=20)

        self.lbl_conn = tk.Label(header,
            text="● Connettendo...",
            font=("Arial", 10), bg="#1a3a5c", fg="#f39c12")
        self.lbl_conn.pack(side="right", padx=20)

    def _build_tabs(self):
        """Crea il notebook con le tre schede."""
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook",        background="#1a3a5c", borderwidth=0)
        style.configure("TNotebook.Tab",    background="#2c5282", foreground="white",
                        padding=[14, 6], font=("Arial", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", "#f5f7fa")],
                  foreground=[("selected", "#1a3a5c")])

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        # Scheda 1 — Dati
        tab_dati = PannelloDati(self.notebook)
        self.notebook.add(tab_dati, text="📋  Dati")

        # Scheda 2 — Grafici
        tab_grafici = PannelloGrafici(self.notebook)
        self.notebook.add(tab_grafici, text="📈  Grafici")

        # Scheda 3 — AI
        tab_ai = PannelloAI(self.notebook)
        self.notebook.add(tab_ai, text="🤖  Pannello AI")

    def _verifica_connessione(self):
        """Controlla la connessione al DB all'avvio."""
        try:
            conn = db.get_connection()
            conn.close()
            self.lbl_conn.config(text="● Database connesso", fg="#2ecc71")
        except Exception as e:
            self.lbl_conn.config(text="● Connessione fallita", fg="#e74c3c")
            messagebox.showerror(
                "Errore di connessione",
                f"Impossibile connettersi al database.\n\n"
                f"Controlla il file .env nella root del progetto.\n\n"
                f"Dettaglio: {e}"
            )


if __name__ == "__main__":
    app = AppAIRE()
    app.mainloop()
