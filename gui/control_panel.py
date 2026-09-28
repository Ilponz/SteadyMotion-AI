"""
Pannello di controllo moderno per SteadyMotion AI.
Interfaccia compatta, scura ed ergonomica per la calibrazione e la personalizzazione
in tempo reale dei parametri di puntamento, filtro anti-tremore e dwell click.
"""

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict


class ControlPanel:
    """Interfaccia grafica principale di controllo e configurazione."""

    def __init__(self, root: tk.Tk, on_param_change: Callable[[str, Any], None], on_recenter: Callable[[], None], on_toggle_pause: Callable[[], None]):
        self.root = root
        self.on_param_change = on_param_change
        self.on_recenter = on_recenter
        self.on_toggle_pause = on_toggle_pause

        self.root.title("SteadyMotion AI • Control Hub")
        self.root.geometry("440x620")
        self.root.minsize(400, 580)
        self.root.config(bg="#0f172a")

        self._setup_style()
        self._build_ui()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#1e293b", relief="flat")
        style.configure(
            "TLabel",
            background="#0f172a",
            foreground="#f8fafc",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Card.TLabel",
            background="#1e293b",
            foreground="#94a3b8",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Title.TLabel",
            background="#0f172a",
            foreground="#38bdf8",
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background="#0f172a",
            foreground="#64748b",
            font=("Segoe UI", 8),
        )
        style.configure(
            "Action.TButton",
            font=("Segoe UI", 9, "bold"),
            padding=6,
            background="#0284c7",
            foreground="#ffffff",
        )
        style.map("Action.TButton", background=[("active", "#0369a1")])

    def _build_ui(self):
        # 1. Intestazione
        header = ttk.Frame(self.root, padding=12)
        header.pack(fill="x")

        ttk.Label(header, text="STEADYMOTION AI", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Sistema Deterministico di Accessibilità Cefalica a Costo Zero",
            style="Subtitle.TLabel",
        ).pack(anchor="w")

        # 2. Sezione Sensibilità & Puntamento
        card_pt = ttk.Frame(self.root, style="Card.TFrame", padding=12)
        card_pt.pack(fill="x", padx=12, pady=6)

        ttk.Label(card_pt, text="SENSIBILITÀ PUNTATORE", style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.gain_val = tk.DoubleVar(value=2.8)
        self._create_slider(card_pt, "Guadagno Movimento Head", self.gain_val, 1.0, 6.0, "gain")

        self.deadzone_val = tk.DoubleVar(value=0.002)
        self._create_slider(card_pt, "Filtro Micro-Tremore (Deadzone)", self.deadzone_val, 0.0005, 0.008, "deadzone")

        # 3. Sezione Filtro One-Euro (Anti-Tremore)
        card_dsp = ttk.Frame(self.root, style="Card.TFrame", padding=12)
        card_dsp.pack(fill="x", padx=12, pady=6)

        ttk.Label(card_dsp, text="FILTRAGGIO DSP (ONE-EURO FILTER)", style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.cutoff_val = tk.DoubleVar(value=1.2)
        self._create_slider(card_dsp, "Stabilità da Fermo (Min Cutoff Hz)", self.cutoff_val, 0.4, 3.0, "min_cutoff")

        self.beta_val = tk.DoubleVar(value=0.008)
        self._create_slider(card_dsp, "Reattività Movimento (Beta)", self.beta_val, 0.001, 0.03, "beta")

        # 4. Sezione Dwell Click
        card_dwell = ttk.Frame(self.root, style="Card.TFrame", padding=12)
        card_dwell.pack(fill="x", padx=12, pady=6)

        ttk.Label(card_dwell, text="CLIC A SOSTA (DWELL CLICK)", style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.dwell_enabled = tk.BooleanVar(value=True)
        chk = tk.Checkbutton(
            card_dwell,
            text="Abilita Clic a Sosta Automatico",
            variable=self.dwell_enabled,
            bg="#1e293b",
            fg="#f8fafc",
            selectcolor="#0f172a",
            activebackground="#1e293b",
            activeforeground="#38bdf8",
            command=lambda: self.on_param_change("dwell_enabled", self.dwell_enabled.get()),
        )
        chk.pack(anchor="w", pady=2)

        self.dwell_time_val = tk.DoubleVar(value=0.65)
        self._create_slider(card_dwell, "Tempo di Sosta (secondi)", self.dwell_time_val, 0.35, 1.5, "dwell_time")

        # 5. Pulsanti di Controllo Rapido
        btn_box = ttk.Frame(self.root, padding=12)
        btn_box.pack(fill="x", pady=4)

        recenter_btn = ttk.Button(btn_box, text="🎯 Ricentra Calibrazione (F12)", style="Action.TButton", command=self.on_recenter)
        recenter_btn.pack(side="left", expand=True, fill="x", padx=4)

        self.pause_btn = ttk.Button(btn_box, text="⏸ Pausa (F9)", style="Action.TButton", command=self.on_toggle_pause)
        self.pause_btn.pack(side="right", expand=True, fill="x", padx=4)

        # 6. Barra di Stato
        self.status_bar = ttk.Frame(self.root, style="Card.TFrame", padding=8)
        self.status_bar.pack(side="bottom", fill="x", padx=12, pady=8)

        self.lbl_fps = ttk.Label(self.status_bar, text="FPS: --", style="Card.TLabel")
        self.lbl_fps.pack(side="left", padx=6)

        self.lbl_face = ttk.Label(self.status_bar, text="Volto: In attesa...", style="Card.TLabel")
        self.lbl_face.pack(side="left", padx=6)

        self.lbl_status = ttk.Label(self.status_bar, text="ATTIVO", style="Card.TLabel", foreground="#10b981", font=("Segoe UI", 9, "bold"))
        self.lbl_status.pack(side="right", padx=6)

    def _create_slider(self, parent, label_text, var, from_, to, param_name):
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=2)

        lbl = ttk.Label(row, text=label_text, style="Card.TLabel")
        lbl.pack(side="left")

        val_lbl = ttk.Label(row, text=f"{var.get():.3f}", style="Card.TLabel", foreground="#38bdf8")
        val_lbl.pack(side="right")

        def _on_change(val):
            v = float(val)
            val_lbl.config(text=f"{v:.3f}")
            self.on_param_change(param_name, v)

        slider = ttk.Scale(parent, from_=from_, to=to, variable=var, orient="horizontal", command=_on_change)
        slider.pack(fill="x", pady=1)

    def update_telemetry(self, fps: float, face_detected: bool, is_blinking: bool, is_paused: bool):
        """Aggiorna i valori in tempo reale sul pannello."""
        self.lbl_fps.config(text=f"FPS: {fps:.1f}")
        if is_paused:
            self.lbl_status.config(text="IN PAUSA", foreground="#eab308")
        elif is_blinking:
            self.lbl_status.config(text="BLINK (CLAMP)", foreground="#38bdf8")
        else:
            self.lbl_status.config(text="ATTIVO", foreground="#10b981")

        if face_detected:
            self.lbl_face.config(text="Volto: Agganciato", foreground="#10b981")
        else:
            self.lbl_face.config(text="Volto: Fuori campo", foreground="#ef4444")
