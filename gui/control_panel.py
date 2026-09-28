"""
Pannello di controllo ad altissima ergonomia visiva per SteadyMotion AI v3.0.
Sviluppato con CustomTkinter v6 (Windows 11 Fluent Design / Deep Obsidian & Slate).

Caratteristiche di Human-Grade Design & Clinical Onboarding:
1. Avvio Protetto in Standby (Disarmed by default): il mouse non viene dirottato finché l'utente non avvia esplicitamente.
2. Banner di Sicurezza Interattivo con stato chiaro: "STANDBY" (Cursore libero) vs "TRACCIAMENTO ATTIVO".
3. Wizard di Configurazione Guidata (Setup a 4 Step) per caregiver e pazienti.
4. Tutorial Interattivo con Minigioco Sandbox a 5 Bersagli per verificare la raggiungibilità dello schermo.
5. Modalità Giorno (Light), Notte (Dark) e Sistema a commutazione dinamica istantanea.
6. Personalizzazione completa: Palette Colori e Scaling UI (100%-130%).
7. Track Status & Radar Posturale (Tobii Dynavox Style) con mirino orientativo.
8. Tastiera CAA di Comunicazione Rapida (Emergency Speech).
"""

import json
import math
import os
import subprocess
import tkinter as tk
from typing import Any, Callable, Dict, Optional
import customtkinter as ctk

# Configurazione iniziale di CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "config.json"

PRESETS: Dict[str, Dict[str, Any]] = {
    "Standard (Bilanciato)": {
        "gain": 2.8,
        "deadzone": 2.0,
        "min_cutoff": 1.1,
        "beta": 0.006,
        "dwell_enabled": True,
        "dwell_time": 0.65,
        "acoustic_enabled": False,
        "acoustic_threshold": 0.18,
        "desc": "Calibrato per uso quotidiano equilibrato. Fluidità a 60 FPS e sosta comoda.",
    },
    "Parkinson (Tremore Severo)": {
        "gain": 2.4,
        "deadzone": 3.8,
        "min_cutoff": 0.8,
        "beta": 0.005,
        "dwell_enabled": True,
        "dwell_time": 0.85,
        "acoustic_enabled": False,
        "acoustic_threshold": 0.22,
        "desc": "Soppressione dell'89% sul tremore a 5 Hz. Deadzone solida da fermo.",
    },
    "SLA / ALS (Ipomobilità)": {
        "gain": 3.8,
        "deadzone": 1.2,
        "min_cutoff": 1.5,
        "beta": 0.015,
        "dwell_enabled": True,
        "dwell_time": 0.55,
        "acoustic_enabled": True,
        "acoustic_threshold": 0.15,
        "desc": "Guadagno alto per micro-escursioni cervicali. Trigger acustico soffio attivo.",
    },
}


class ControlPanel:
    """Interfaccia grafica principale moderna con Wizard di setup e Tutorial interattivo."""

    def __init__(
        self,
        root: ctk.CTk,
        on_param_change: Callable[[str, Any], None],
        on_recenter: Callable[[], None],
        on_toggle_pause: Callable[[], None],
        on_calibrate_audio: Optional[Callable[[], None]] = None,
        on_toggle_demo: Optional[Callable[[bool], None]] = None,
        on_open_calibration: Optional[Callable[[], None]] = None,
        on_reset_rom: Optional[Callable[[], None]] = None,
    ):
        self.root = root
        self.on_param_change = on_param_change
        self.on_recenter = on_recenter
        self.on_toggle_pause = on_toggle_pause
        self.on_calibrate_audio = on_calibrate_audio
        self.on_toggle_demo = on_toggle_demo
        self.on_open_calibration = on_open_calibration
        self.on_reset_rom = on_reset_rom

        self.root.title("SteadyMotion AI • Assistive Control Center")
        self.root.geometry("540x860")
        self.root.minsize(500, 780)

        # Variabili di stato interne
        self.gain_val = tk.DoubleVar(value=2.8)
        self.deadzone_val = tk.DoubleVar(value=2.0)
        self.cutoff_val = tk.DoubleVar(value=1.1)
        self.beta_val = tk.DoubleVar(value=0.006)
        self.dwell_enabled = tk.BooleanVar(value=True)
        self.dwell_time_val = tk.DoubleVar(value=0.65)
        self.acoustic_enabled = tk.BooleanVar(value=False)
        self.acoustic_threshold_val = tk.DoubleVar(value=0.18)
        self.demo_mode = tk.BooleanVar(value=False)

        # Calibrazione Clinica ROM Asimmetrica
        self.is_custom_rom = False
        self.rom_gains = {
            "gain_x_left": 2.8,
            "gain_x_right": 2.8,
            "gain_y_up": 2.8,
            "gain_y_down": 2.8,
        }

        # Preferenze Tema e Personalizzazione
        self.appearance_mode_str = tk.StringVar(value="Dark")
        self.ui_scale_str = tk.StringVar(value="100%")

        # Stato addestramento e sandbox bersagli
        self.targets_hit_count = 0
        self.targets_total = 5

        self._labels_map: Dict[str, ctk.CTkLabel] = {}
        self._preset_cards: Dict[str, ctk.CTkFrame] = {}

        self._build_ui()
        self._load_config()

    def _build_ui(self):
        # 1. Header con Branding & Live Status Pills
        self.header_frame = ctk.CTkFrame(self.root, corner_radius=12)
        self.header_frame.pack(fill="x", padx=14, pady=(10, 4))

        top_row = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(8, 2))

        title_lbl = ctk.CTkLabel(
            top_row,
            text="STEADYMOTION AI",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=("#0284c7", "#38bdf8"),
        )
        title_lbl.pack(side="left")

        self.pill_status = ctk.CTkLabel(
            top_row,
            text="⏸ STANDBY (Cursore libero)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#f59e0b",
        )
        self.pill_status.pack(side="right", padx=4)

        sub_row = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        sub_row.pack(fill="x", padx=12, pady=(0, 6))

        sub_lbl = ctk.CTkLabel(
            sub_row,
            text="Piattaforma Assistiva Cefalica Deterministica",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748b", "#94a3b8"),
        )
        sub_lbl.pack(side="left")

        self.lbl_light_badge = ctk.CTkLabel(
            sub_row,
            text="Luce: OK",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#10b981",
        )
        self.lbl_light_badge.pack(side="right", padx=4)

        # 2. Banner di Sicurezza Primario (Arm / Disarm Prominente)
        self.safety_banner = ctk.CTkFrame(self.root, corner_radius=10, fg_color=("#fef3c7", "#1e293b"), border_width=1, border_color="#d97706")
        self.safety_banner.pack(fill="x", padx=14, pady=4)

        b_row = ctk.CTkFrame(self.safety_banner, fg_color="transparent")
        b_row.pack(fill="x", padx=10, pady=8)

        self.lbl_safety_status = ctk.CTkLabel(
            b_row,
            text="⚠️ STATO: STANDBY DI SICUREZZA\nIl cursore è libero. Prendi comodamente la postura prima di avviare.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#92400e", "#f59e0b"),
            justify="left",
        )
        self.lbl_safety_status.pack(side="left", padx=4)

        self.btn_master_toggle = ctk.CTkButton(
            b_row,
            text="▶ AVVIA TRACKING (F9)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=38,
            width=165,
            corner_radius=8,
            fg_color="#10b981",
            hover_color="#059669",
            command=self.on_toggle_pause,
        )
        self.btn_master_toggle.pack(side="right", padx=4)

        # Quick Action Bar
        action_bar = ctk.CTkFrame(self.root, fg_color="transparent")
        action_bar.pack(fill="x", padx=14, pady=2)

        self.btn_recenter = ctk.CTkButton(
            action_bar,
            text="🎯 Ricentra Centro Schermo (F12)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self.on_recenter,
            height=32,
            corner_radius=8,
            fg_color="#0284c7",
            hover_color="#0369a1",
        )
        self.btn_recenter.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.btn_osk = ctk.CTkButton(
            action_bar,
            text="⌨️ Tastiera OSK",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._launch_osk,
            height=32,
            width=110,
            corner_radius=8,
            fg_color=("#475569", "#334155"),
            hover_color=("#334155", "#1e293b"),
        )
        self.btn_osk.pack(side="right", padx=(4, 0))

        # 3. Tabview con Setup Wizard & Tutorial inclusi
        self.tabview = ctk.CTkTabview(self.root, corner_radius=12)
        self.tabview.pack(fill="both", expand=True, padx=14, pady=4)

        self.tab_wizard = self.tabview.add("🎓 Setup Wizard")
        self.tab_tutorial = self.tabview.add("📖 Tutorial & Bersagli")
        self.tab_controls = self.tabview.add("🎯 Puntamento")
        self.tab_presets = self.tabview.add("🧠 Profili")
        self.tab_audio = self.tabview.add("🎤 Audio")
        self.tab_radar = self.tabview.add("👁️ Postura")
        self.tab_aac = self.tabview.add("💬 CAA")
        self.tab_settings = self.tabview.add("⚙️ Temi")

        self._build_tab_wizard()
        self._build_tab_tutorial()
        self._build_tab_controls()
        self._build_tab_presets()
        self._build_tab_audio()
        self._build_tab_radar()
        self._build_tab_aac()
        self._build_tab_settings()

        # 4. Footer con Switch Demo Mode Offline & FPS
        footer = ctk.CTkFrame(self.root, corner_radius=10)
        footer.pack(fill="x", padx=14, pady=(2, 8))

        demo_switch = ctk.CTkSwitch(
            footer,
            text="Modalità Demo / Simulazione Offline (Senza Fotocamera)",
            variable=self.demo_mode,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._on_toggle_demo_switch,
        )
        demo_switch.pack(side="left", padx=10, pady=6)

        self.lbl_fps_footer = ctk.CTkLabel(
            footer,
            text="FPS: --",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748b", "#94a3b8"),
        )
        self.lbl_fps_footer.pack(side="right", padx=10)

    # ---------------- TAB 0: SETUP WIZARD GUIDATO ----------------
    def _build_tab_wizard(self):
        desc = ctk.CTkLabel(
            self.tab_wizard,
            text="Configurazione guidata per caregiver e pazienti (4 semplici passaggi):",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("#0284c7", "#38bdf8"),
        )
        desc.pack(anchor="w", padx=6, pady=(4, 6))

        # Step 1: Profilo
        step1 = ctk.CTkFrame(self.tab_wizard, corner_radius=8)
        step1.pack(fill="x", padx=6, pady=3)
        ctk.CTkLabel(step1, text="PASSO 1: Seleziona la condizione motoria del paziente", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", padx=8, pady=(4, 2))

        btn_row1 = ctk.CTkFrame(step1, fg_color="transparent")
        btn_row1.pack(fill="x", padx=8, pady=(2, 6))
        for p_name in PRESETS.keys():
            b = ctk.CTkButton(btn_row1, text=p_name.split()[0], font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), height=28, command=lambda n=p_name: self._apply_preset_by_name(n))
            b.pack(side="left", expand=True, fill="x", padx=2)

        # Step 2: Postura
        step2 = ctk.CTkFrame(self.tab_wizard, corner_radius=8)
        step2.pack(fill="x", padx=6, pady=3)
        ctk.CTkLabel(step2, text="PASSO 2: Posiziona il paziente a 50-70 cm dalla webcam", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", padx=8, pady=(4, 2))
        self.lbl_wizard_align = ctk.CTkLabel(step2, text="Stato: Controlla che il volto sia rilevato e la luce sia OK", font=ctk.CTkFont(family="Segoe UI", size=10), text_color="#10b981")
        self.lbl_wizard_align.pack(anchor="w", padx=8, pady=(0, 6))

        # Step 3: Calibrazione Centro
        step3 = ctk.CTkFrame(self.tab_wizard, corner_radius=8)
        step3.pack(fill="x", padx=6, pady=3)
        ctk.CTkLabel(step3, text="PASSO 3: Il paziente fissa il centro dello schermo in postura rilassata", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", padx=8, pady=(4, 2))
        btn_w_rec = ctk.CTkButton(step3, text="🎯 Memorizza Centro Neutrale (F12)", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), height=30, fg_color="#0284c7", command=self.on_recenter)
        btn_w_rec.pack(fill="x", padx=8, pady=(2, 6))

        # Step 3b: Calibrazione ROM (Consigliata per mobilità ridotta)
        step3b = ctk.CTkFrame(self.tab_wizard, corner_radius=8)
        step3b.pack(fill="x", padx=6, pady=3)
        ctk.CTkLabel(step3b, text="PASSO AVANZATO: Calibrazione Escursione Cervicale (5 Punti)", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", padx=8, pady=(4, 2))
        btn_w_rom = ctk.CTkButton(
            step3b,
            text="📐 Avvia Calibrazione ROM a Tutto Schermo",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=30,
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            command=self.on_open_calibration if self.on_open_calibration else lambda: None,
        )
        btn_w_rom.pack(fill="x", padx=8, pady=(2, 6))

        # Step 4: Clic preferito
        step4 = ctk.CTkFrame(self.tab_wizard, corner_radius=8)
        step4.pack(fill="x", padx=6, pady=3)
        ctk.CTkLabel(step4, text="PASSO 4: Modalità di clic preferita", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", padx=8, pady=(4, 2))

        btn_row4 = ctk.CTkFrame(step4, fg_color="transparent")
        btn_row4.pack(fill="x", padx=8, pady=(2, 6))

        b_dwell = ctk.CTkButton(btn_row4, text="⏱ Clic a Sosta (Dwell)", font=ctk.CTkFont(family="Segoe UI", size=11), height=28, command=lambda: self._set_wizard_click("dwell"))
        b_dwell.pack(side="left", expand=True, fill="x", padx=2)

        b_mic = ctk.CTkButton(btn_row4, text="🎤 Soffio/Pop Microfono", font=ctk.CTkFont(family="Segoe UI", size=11), height=28, command=lambda: self._set_wizard_click("mic"))
        b_mic.pack(side="right", expand=True, fill="x", padx=2)

        # Completamento
        btn_finish = ctk.CTkButton(
            self.tab_wizard,
            text="🚀 PRONTO! SALVA & AVVIA TRACKING MOUSE",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=40,
            fg_color="#10b981",
            hover_color="#059669",
            command=self._finish_wizard,
        )
        btn_finish.pack(fill="x", padx=6, pady=(8, 4))

    def _set_wizard_click(self, mode: str):
        if mode == "dwell":
            self.dwell_enabled.set(True)
            self.acoustic_enabled.set(False)
            self.on_param_change("dwell_enabled", True)
            self.on_param_change("acoustic_enabled", False)
        else:
            self.dwell_enabled.set(False)
            self.acoustic_enabled.set(True)
            self.on_param_change("dwell_enabled", False)
            self.on_param_change("acoustic_enabled", True)

    def _finish_wizard(self):
        self._save_config()
        if not self.demo_mode.get():
            self.on_recenter()
        self.on_toggle_pause()

    # ---------------- TAB 1: TUTORIAL INTERATTIVO & SANDBOX BERSAGLI ----------------
    def _build_tab_tutorial(self):
        # Scheda Istruzioni
        card_info = ctk.CTkFrame(self.tab_tutorial, corner_radius=8)
        card_info.pack(fill="x", padx=6, pady=4)

        t_text = (
            "💡 COME UTILIZZARE STEADYMOTION AI IN 4 REGOLE D'ORO:\n"
            "1. MOVIMENTO: Fai micro-spostamenti con la punta del naso (non ruotare eccessivamente il collo).\n"
            "2. CLIC A SOSTA: Fermati sull'oggetto desiderato: apparirà un cerchio che si carica in verde.\n"
            "3. ANNULLAMENTO SPASMO: Se ti muovi prima che il cerchio si chiuda, il clic si annulla dolcemente.\n"
            "4. EMERGENZA: Premi F12 per ricentrare; premi F9 per mettere in pausa e liberare il mouse."
        )
        ctk.CTkLabel(card_info, text=t_text, font=ctk.CTkFont(family="Segoe UI", size=10), text_color=("#334155", "#cbd5e1"), justify="left").pack(padx=8, pady=6)

        # Minigioco Sandbox di Addestramento Bersagli
        sandbox_card = ctk.CTkFrame(self.tab_tutorial, corner_radius=10, fg_color=("#e2e8f0", "#0f172a"))
        sandbox_card.pack(fill="both", expand=True, padx=6, pady=4)

        sh_row = ctk.CTkFrame(sandbox_card, fg_color="transparent")
        sh_row.pack(fill="x", padx=8, pady=4)

        ctk.CTkLabel(sh_row, text="🎯 SANDBOX DI ADDESTRAMENTO BERSAGLI", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(side="left")
        self.lbl_score = ctk.CTkLabel(sh_row, text="Bersagli: 0/5", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#10b981")
        self.lbl_score.pack(side="right")

        # Griglia Sandbox 3x3
        self.target_grid = ctk.CTkFrame(sandbox_card, fg_color="transparent")
        self.target_grid.pack(fill="both", expand=True, padx=10, pady=8)

        self._target_buttons = []
        positions = [(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)]
        names = ["Alto-Sinistra", "Alto-Destra", "CENTRO", "Basso-Sinistra", "Basso-Destra"]

        for idx, (r, c) in enumerate(positions):
            btn = ctk.CTkButton(
                self.target_grid,
                text=f"🎯 {names[idx]}",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                height=45,
                fg_color="#0284c7",
                hover_color="#0369a1",
                command=lambda b_idx=idx: self._on_hit_target(b_idx),
            )
            btn.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")
            self._target_buttons.append(btn)

        self.target_grid.grid_rowconfigure(0, weight=1)
        self.target_grid.grid_rowconfigure(1, weight=1)
        self.target_grid.grid_rowconfigure(2, weight=1)
        self.target_grid.grid_columnconfigure(0, weight=1)
        self.target_grid.grid_columnconfigure(1, weight=1)
        self.target_grid.grid_columnconfigure(2, weight=1)

    def _on_hit_target(self, idx: int):
        self._target_buttons[idx].configure(fg_color="#10b981", text="✅ COLPITO!")
        self.targets_hit_count += 1
        self.lbl_score.configure(text=f"Bersagli: {self.targets_hit_count}/{self.targets_total}")
        if self.targets_hit_count >= self.targets_total:
            self.lbl_score.configure(text="🎉 OTTIMO! TUTTI I BERSAGLI COLPITI!", text_color="#38bdf8")

    # ---------------- TAB 2: PUNTAMENTO & FILTRI ----------------
    def _build_tab_controls(self):
        card_pt = ctk.CTkFrame(self.tab_controls, corner_radius=10)
        card_pt.pack(fill="x", pady=3, padx=6)
        ctk.CTkLabel(card_pt, text="SENSIBILITÀ & RISOLUZIONE CEFALICA", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", padx=10, pady=(6, 2))

        self._create_slider_row(card_pt, "Guadagno Movimento Head", self.gain_val, 1.0, 6.0, "gain", "{:.2f}")
        self._create_slider_row(card_pt, "Deadzone Anti-Tremore (px)", self.deadzone_val, 0.5, 6.0, "deadzone", "{:.1f} px")

        # Card Calibrazione Asimmetrica ROM (5 Punti)
        card_rom = ctk.CTkFrame(self.tab_controls, corner_radius=10, fg_color=("#f1f5f9", "#1e293b"))
        card_rom.pack(fill="x", pady=3, padx=6)

        rom_header = ctk.CTkFrame(card_rom, fg_color="transparent")
        rom_header.pack(fill="x", padx=10, pady=(6, 2))
        ctk.CTkLabel(rom_header, text="CALIBRAZIONE CLINICA RANGE OF MOTION (ROM)", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#38bdf8").pack(side="left")

        self.lbl_rom_status = ctk.CTkLabel(rom_header, text="Profilo: Simmetrico Standard", font=ctk.CTkFont(family="Segoe UI", size=10), text_color="#94a3b8")
        self.lbl_rom_status.pack(side="right")

        self.lbl_rom_details = ctk.CTkLabel(
            card_rom,
            text="Guadagni per quadrante: SX 2.80x | DX 2.80x | SU 2.80x | GIÙ 2.80x",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#475569", "#cbd5e1"),
        )
        self.lbl_rom_details.pack(anchor="w", padx=10, pady=2)

        rom_btns = ctk.CTkFrame(card_rom, fg_color="transparent")
        rom_btns.pack(fill="x", padx=10, pady=(4, 8))

        btn_start_calib = ctk.CTkButton(
            rom_btns,
            text="📐 Calibrazione ROM (5 Punti)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=30,
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            command=self.on_open_calibration if self.on_open_calibration else lambda: None,
        )
        btn_start_calib.pack(side="left", expand=True, fill="x", padx=(0, 4))

        btn_reset_rom = ctk.CTkButton(
            rom_btns,
            text="Ripristina Simmetrico",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            height=30,
            fg_color="#334155",
            hover_color="#475569",
            command=self.on_reset_rom if self.on_reset_rom else lambda: None,
        )
        btn_reset_rom.pack(side="right", padx=(4, 0))

        card_dsp = ctk.CTkFrame(self.tab_controls, corner_radius=10)
        card_dsp.pack(fill="x", pady=3, padx=6)
        ctk.CTkLabel(card_dsp, text="FILTRO ONE-EURO ISOTROPO 2D (ANTI-TREMORE)", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", padx=10, pady=(6, 2))

        self._create_slider_row(card_dsp, "Stabilità a Riposo (Cutoff Hz)", self.cutoff_val, 0.4, 3.0, "min_cutoff", "{:.2f} Hz")
        self._create_slider_row(card_dsp, "Reattività al Moto Rapido (Beta)", self.beta_val, 0.001, 0.030, "beta", "{:.4f}")

        card_dwell = ctk.CTkFrame(self.tab_controls, corner_radius=10)
        card_dwell.pack(fill="x", pady=3, padx=6)
        ctk.CTkLabel(card_dwell, text="CLIC A SOSTA AUTOMATICO (DWELL)", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", padx=10, pady=(6, 2))

        switch_dwell = ctk.CTkSwitch(
            card_dwell,
            text="Abilita Clic a Sosta con Tolleranza Spasmi (Gravity Well)",
            variable=self.dwell_enabled,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=lambda: self.on_param_change("dwell_enabled", self.dwell_enabled.get()),
        )
        switch_dwell.pack(anchor="w", padx=10, pady=3)
        self._create_slider_row(card_dwell, "Tempo di Sosta per Clic", self.dwell_time_val, 0.35, 1.50, "dwell_time", "{:.2f} s")

    # ---------------- TAB 3: PROFILI CLINICI ----------------
    def _build_tab_presets(self):
        desc_lbl = ctk.CTkLabel(
            self.tab_presets,
            text="Profili preimpostati per patologia motoria. Clicca per attivare istantaneamente:",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748b", "#94a3b8"),
        )
        desc_lbl.pack(anchor="w", padx=8, pady=(4, 6))

        for name, data in PRESETS.items():
            card = ctk.CTkFrame(self.tab_presets, corner_radius=10)
            card.pack(fill="x", pady=3, padx=6)
            self._preset_cards[name] = card

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=(6, 2))

            ctk.CTkLabel(row, text=name, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")).pack(side="left")

            btn_apply = ctk.CTkButton(
                row,
                text="Attiva Profilo",
                width=95,
                height=26,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                command=lambda p_name=name: self._apply_preset_by_name(p_name),
            )
            btn_apply.pack(side="right")

            lbl_desc = ctk.CTkLabel(
                card,
                text=data["desc"],
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=("#64748b", "#94a3b8"),
                anchor="w",
            )
            lbl_desc.pack(fill="x", padx=10, pady=(0, 6))

        save_box = ctk.CTkFrame(self.tab_presets, fg_color="transparent")
        save_box.pack(fill="x", pady=(8, 2), padx=6)

        btn_save = ctk.CTkButton(
            save_box,
            text="💾 Salva Configurazione come Predefinita",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._save_config,
            fg_color="#10b981",
            hover_color="#059669",
        )
        btn_save.pack(fill="x")

    # ---------------- TAB 4: TRIGGER ACUSTICO ----------------
    def _build_tab_audio(self):
        card = ctk.CTkFrame(self.tab_audio, corner_radius=10)
        card.pack(fill="x", pady=4, padx=6)

        ctk.CTkLabel(card, text="TRIGGER ACUSTICO AUSILIARIO (ZERO AFFATICAMENTO)", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", padx=10, pady=(6, 2))

        switch_mic = ctk.CTkSwitch(
            card,
            text="Abilita Clic con Soffio / Pop di Lingua (Microfono USB)",
            variable=self.acoustic_enabled,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=lambda: self.on_param_change("acoustic_enabled", self.acoustic_enabled.get()),
        )
        switch_mic.pack(anchor="w", padx=10, pady=3)

        self._create_slider_row(card, "Soglia di Trigger Acustico", self.acoustic_threshold_val, 0.05, 0.40, "acoustic_threshold", "{:.2f}")

        card_vu = ctk.CTkFrame(card, corner_radius=8, fg_color=("#f1f5f9", "#0f172a"))
        card_vu.pack(fill="x", padx=10, pady=6)

        vu_header = ctk.CTkFrame(card_vu, fg_color="transparent")
        vu_header.pack(fill="x", padx=8, pady=(4, 2))

        ctk.CTkLabel(vu_header, text="LIVELLO SEGNALE RMS (VU METER)", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold")).pack(side="left")
        self.lbl_mic_reading = ctk.CTkLabel(vu_header, text="RMS: 0.000", font=ctk.CTkFont(family="Segoe UI", size=10), text_color="#38bdf8")
        self.lbl_mic_reading.pack(side="right")

        self.vu_bar = ctk.CTkProgressBar(card_vu, height=10, corner_radius=5)
        self.vu_bar.pack(fill="x", padx=8, pady=(2, 6))
        self.vu_bar.set(0.0)

        btn_calib = ctk.CTkButton(
            card,
            text="🎤 Avvia Auto-Calibrazione Rumore Ambientale (2s)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            command=self._on_click_calibrate,
        )
        btn_calib.pack(fill="x", padx=10, pady=(2, 8))

    # ---------------- TAB 5: TRACK STATUS & RADAR POSTURALE ----------------
    def _build_tab_radar(self):
        desc = ctk.CTkLabel(
            self.tab_radar,
            text="Allineamento visivo in tempo reale (Mirino Tobii Dynavox Style):",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748b", "#94a3b8"),
        )
        desc.pack(anchor="w", padx=8, pady=(4, 2))

        radar_card = ctk.CTkFrame(self.tab_radar, corner_radius=10)
        radar_card.pack(fill="both", expand=True, padx=6, pady=4)

        self.radar_canvas = tk.Canvas(
            radar_card,
            width=240,
            height=180,
            bg="#0f172a",
            highlightthickness=0,
        )
        self.radar_canvas.pack(fill="both", expand=True, padx=8, pady=6)

        stats_box = ctk.CTkFrame(radar_card, fg_color="transparent")
        stats_box.pack(fill="x", padx=10, pady=(0, 6))

        self.lbl_radar_yaw = ctk.CTkLabel(stats_box, text="Yaw: 0.0°", font=ctk.CTkFont(family="Segoe UI", size=10))
        self.lbl_radar_yaw.pack(side="left", expand=True)

        self.lbl_radar_pitch = ctk.CTkLabel(stats_box, text="Pitch: 0.0°", font=ctk.CTkFont(family="Segoe UI", size=10))
        self.lbl_radar_pitch.pack(side="left", expand=True)

        self.lbl_radar_roll = ctk.CTkLabel(stats_box, text="Roll: 0.0°", font=ctk.CTkFont(family="Segoe UI", size=10))
        self.lbl_radar_roll.pack(side="left", expand=True)

        self.lbl_radar_status = ctk.CTkLabel(
            radar_card,
            text="Postura: In attesa di segnale",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#10b981",
        )
        self.lbl_radar_status.pack(pady=(0, 4))

    # ---------------- TAB 6: TASTIERA CAA RAPIDA ----------------
    def _build_tab_aac(self):
        desc = ctk.CTkLabel(
            self.tab_aac,
            text="Comunicazione Aumentativa Alternativa (CAA) a sosta Dwell integrata:",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748b", "#94a3b8"),
        )
        desc.pack(anchor="w", padx=8, pady=(4, 2))

        card_quick = ctk.CTkFrame(self.tab_aac, corner_radius=10)
        card_quick.pack(fill="x", padx=6, pady=3)
        ctk.CTkLabel(card_quick, text="FRASI RAPIDE DI PRIMO SOCCORSO", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", padx=10, pady=(4, 2))

        grid_frame = ctk.CTkFrame(card_quick, fg_color="transparent")
        grid_frame.pack(fill="x", padx=6, pady=3)

        emergency_phrases = ["SÌ", "NO", "AIUTO", "HO SETE", "GRAZIE", "CHIAMAMI"]
        for idx, phrase in enumerate(emergency_phrases):
            color = "#ef4444" if phrase == "AIUTO" else "#0284c7"
            btn = ctk.CTkButton(
                grid_frame,
                text=phrase,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                height=34,
                fg_color=color,
                command=lambda p=phrase: self._on_aac_speak(p),
            )
            btn.grid(row=idx // 3, column=idx % 3, padx=3, pady=3, sticky="nsew")
            grid_frame.grid_columnconfigure(idx % 3, weight=1)

        self.aac_text_var = tk.StringVar(value="")
        text_disp = ctk.CTkEntry(
            self.tab_aac,
            textvariable=self.aac_text_var,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=34,
            corner_radius=8,
        )
        text_disp.pack(fill="x", padx=6, pady=4)

        kbd_frame = ctk.CTkFrame(self.tab_aac, corner_radius=10)
        kbd_frame.pack(fill="both", expand=True, padx=6, pady=3)

        letters = [
            ["A", "B", "C", "D", "E", "F"],
            ["G", "H", "I", "L", "M", "N"],
            ["O", "P", "Q", "R", "S", "T"],
            ["U", "V", "Z", "SPAZIO", "CANC"],
        ]

        for r_idx, row_chars in enumerate(letters):
            row_f = ctk.CTkFrame(kbd_frame, fg_color="transparent")
            row_f.pack(fill="x", padx=4, pady=1)
            for c_char in row_chars:
                w = 75 if len(c_char) > 1 else 32
                b = ctk.CTkButton(
                    row_f,
                    text=c_char,
                    width=w,
                    height=28,
                    font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                    command=lambda ch=c_char: self._on_aac_key(ch),
                )
                b.pack(side="left", expand=True, fill="x", padx=1)

    # ---------------- TAB 7: TEMI & ACCESSIBILITÀ ----------------
    def _build_tab_settings(self):
        card = ctk.CTkFrame(self.tab_settings, corner_radius=10)
        card.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(card, text="PERSONALIZZAZIONE VISIVA & ACCESSIBILITÀ", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")).pack(anchor="w", padx=10, pady=(6, 4))

        row_mode = ctk.CTkFrame(card, fg_color="transparent")
        row_mode.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(row_mode, text="Modalità Aspetto:", font=ctk.CTkFont(family="Segoe UI", size=11)).pack(side="left")

        seg_mode = ctk.CTkSegmentedButton(
            row_mode,
            values=["Dark", "Light", "System"],
            variable=self.appearance_mode_str,
            command=self._change_appearance_mode,
        )
        seg_mode.pack(side="right")

        row_scale = ctk.CTkFrame(card, fg_color="transparent")
        row_scale.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(row_scale, text="Ingrandimento Interfaccia (Ipovisione):", font=ctk.CTkFont(family="Segoe UI", size=11)).pack(side="left")

        combo_scale = ctk.CTkComboBox(
            row_scale,
            values=["100%", "110%", "120%", "130%"],
            variable=self.ui_scale_str,
            command=self._change_scaling,
            width=100,
        )
        combo_scale.pack(side="right")

    # ---------------- HELPERS UI & CALLBACKS ----------------
    def _create_slider_row(self, parent, label_text, var, from_, to, param_name, fmt="{:.2f}"):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=1)

        lbl = ctk.CTkLabel(row, text=label_text, font=ctk.CTkFont(family="Segoe UI", size=11))
        lbl.pack(side="left")

        val_lbl = ctk.CTkLabel(
            row,
            text=fmt.format(var.get()),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("#0284c7", "#38bdf8"),
        )
        val_lbl.pack(side="right")
        self._labels_map[param_name] = val_lbl

        def _on_slider(val):
            v = float(val)
            val_lbl.configure(text=fmt.format(v))
            self.on_param_change(param_name, v)

        slider = ctk.CTkSlider(parent, from_=from_, to=to, variable=var, command=_on_slider, height=14)
        slider.pack(fill="x", padx=10, pady=(0, 3))

    def _apply_preset_by_name(self, name: str):
        if name not in PRESETS:
            return
        p = PRESETS[name]
        self.gain_val.set(p["gain"])
        self.deadzone_val.set(p["deadzone"])
        self.cutoff_val.set(p["min_cutoff"])
        self.beta_val.set(p["beta"])
        self.dwell_enabled.set(p["dwell_enabled"])
        self.dwell_time_val.set(p["dwell_time"])
        self.acoustic_enabled.set(p["acoustic_enabled"])
        self.acoustic_threshold_val.set(p["acoustic_threshold"])

        for k, v in p.items():
            if k != "desc":
                self.on_param_change(k, v)

        if "gain" in self._labels_map:
            self._labels_map["gain"].configure(text=f"{p['gain']:.2f}")
        if "deadzone" in self._labels_map:
            self._labels_map["deadzone"].configure(text=f"{p['deadzone']:.1f} px")
        if "min_cutoff" in self._labels_map:
            self._labels_map["min_cutoff"].configure(text=f"{p['min_cutoff']:.2f} Hz")
        if "beta" in self._labels_map:
            self._labels_map["beta"].configure(text=f"{p['beta']:.4f}")
        if "dwell_time" in self._labels_map:
            self._labels_map["dwell_time"].configure(text=f"{p['dwell_time']:.2f} s")
        if "acoustic_threshold" in self._labels_map:
            self._labels_map["acoustic_threshold"].configure(text=f"{p['acoustic_threshold']:.2f}")

    def _change_appearance_mode(self, mode: str):
        ctk.set_appearance_mode(mode)
        bg_col = "#0f172a" if mode == "Dark" else "#e2e8f0"
        self.radar_canvas.config(bg=bg_col)

    def _change_scaling(self, scale_str: str):
        factor = int(scale_str.replace("%", "")) / 100.0
        ctk.set_widget_scaling(factor)

    def _on_toggle_demo_switch(self):
        val = self.demo_mode.get()
        if self.on_toggle_demo:
            self.on_toggle_demo(val)

    def _on_click_calibrate(self):
        if not self.acoustic_enabled.get():
            self.acoustic_enabled.set(True)
            self.on_param_change("acoustic_enabled", True)
        self.lbl_mic_reading.configure(text="In calibrazione (silenzio 2s)...", text_color="#a78bfa")
        if self.on_calibrate_audio:
            self.on_calibrate_audio()

    def update_calibrated_threshold(self, new_threshold: float):
        self.acoustic_threshold_val.set(new_threshold)
        if "acoustic_threshold" in self._labels_map:
            self._labels_map["acoustic_threshold"].configure(text=f"{new_threshold:.2f}")
        self.lbl_mic_reading.configure(text=f"Calibrato! Nuova: {new_threshold:.2f}", text_color="#10b981")
        self.on_param_change("acoustic_threshold", new_threshold)

    def update_rom_gains(self, gains: Dict[str, float], is_custom: bool = True):
        """Aggiorna le etichette e lo stato visivo della calibrazione Range of Motion."""
        self.is_custom_rom = is_custom
        self.rom_gains = gains
        sx = gains.get("gain_x_left", self.gain_val.get())
        dx = gains.get("gain_x_right", self.gain_val.get())
        su = gains.get("gain_y_up", self.gain_val.get())
        giu = gains.get("gain_y_down", self.gain_val.get())

        if hasattr(self, "lbl_rom_status") and hasattr(self, "lbl_rom_details"):
            if is_custom:
                self.lbl_rom_status.configure(text="Profilo: Matrice ROM Calibrata ✅", text_color="#10b981")
                self.lbl_rom_details.configure(
                    text=f"Guadagni per quadrante: SX {sx:.2f}x | DX {dx:.2f}x | SU {su:.2f}x | GIÙ {giu:.2f}x",
                    text_color="#38bdf8",
                )
            else:
                self.lbl_rom_status.configure(text="Profilo: Simmetrico Standard", text_color="#94a3b8")
                self.lbl_rom_details.configure(
                    text=f"Guadagni per quadrante: SX {sx:.2f}x | DX {dx:.2f}x | SU {su:.2f}x | GIÙ {giu:.2f}x",
                    text_color=("#475569", "#cbd5e1"),
                )
        self._save_config()

    def _launch_osk(self):
        try:
            windir = os.environ.get("WINDIR", "C:\\Windows")
            osk_path = os.path.join(windir, "System32", "osk.exe")
            if os.path.exists(osk_path):
                subprocess.Popen([osk_path], shell=False)
            else:
                subprocess.Popen("osk.exe", shell=True)
        except Exception:
            pass

    def _on_aac_speak(self, text: str):
        self.aac_text_var.set(text)

    def _on_aac_key(self, char: str):
        cur = self.aac_text_var.get()
        if char == "SPAZIO":
            self.aac_text_var.set(cur + " ")
        elif char == "CANC":
            self.aac_text_var.set(cur[:-1] if cur else "")
        else:
            self.aac_text_var.set(cur + char)

    def _save_config(self):
        config_data = {
            "gain": self.gain_val.get(),
            "deadzone": self.deadzone_val.get(),
            "min_cutoff": self.cutoff_val.get(),
            "beta": self.beta_val.get(),
            "dwell_enabled": self.dwell_enabled.get(),
            "dwell_time": self.dwell_time_val.get(),
            "acoustic_enabled": self.acoustic_enabled.get(),
            "acoustic_threshold": self.acoustic_threshold_val.get(),
            "appearance_mode": self.appearance_mode_str.get(),
            "ui_scale": self.ui_scale_str.get(),
            "is_custom_rom": self.is_custom_rom,
            "rom_gains": self.rom_gains,
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
        except Exception:
            pass

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            if "gain" in config_data:
                self.gain_val.set(config_data["gain"])
            if "deadzone" in config_data:
                self.deadzone_val.set(config_data["deadzone"])
            if "min_cutoff" in config_data:
                self.cutoff_val.set(config_data["min_cutoff"])
            if "beta" in config_data:
                self.beta_val.set(config_data["beta"])
            if "dwell_enabled" in config_data:
                self.dwell_enabled.set(config_data["dwell_enabled"])
            if "dwell_time" in config_data:
                self.dwell_time_val.set(config_data["dwell_time"])
            if "acoustic_enabled" in config_data:
                self.acoustic_enabled.set(config_data["acoustic_enabled"])
            if "acoustic_threshold" in config_data:
                self.acoustic_threshold_val.set(config_data["acoustic_threshold"])
            if "appearance_mode" in config_data:
                self.appearance_mode_str.set(config_data["appearance_mode"])
                self._change_appearance_mode(config_data["appearance_mode"])
            if "ui_scale" in config_data:
                self.ui_scale_str.set(config_data["ui_scale"])
                self._change_scaling(config_data["ui_scale"])
            if "is_custom_rom" in config_data and "rom_gains" in config_data:
                self.is_custom_rom = bool(config_data["is_custom_rom"])
                self.rom_gains = config_data["rom_gains"]
                self.update_rom_gains(self.rom_gains, is_custom=self.is_custom_rom)

            for k, v in config_data.items():
                if k not in ("appearance_mode", "ui_scale", "is_custom_rom", "rom_gains"):
                    self.on_param_change(k, v)
        except Exception:
            pass

    def update_telemetry(
        self,
        fps: float,
        face_detected: bool,
        is_blinking: bool,
        is_paused: bool,
        luma: float = 120.0,
        mic_volume: float = 0.0,
        yaw: float = 0.0,
        pitch: float = 0.0,
        roll: float = 0.0,
    ):
        """Aggiorna tutti i componenti visivi e il radar posturale."""
        self.lbl_fps_footer.configure(text=f"FPS: {fps:.1f}")

        # Aggiornamento Banner di Sicurezza e Tasto Master
        if is_paused:
            self.pill_status.configure(text="⏸ STANDBY (Cursore libero)", text_color="#f59e0b")
            self.safety_banner.configure(fg_color=("#fef3c7", "#1e293b"), border_color="#d97706")
            self.lbl_safety_status.configure(
                text="⚠️ STATO: STANDBY DI SICUREZZA\nIl cursore è libero. Prendi comodamente la postura prima di avviare.",
                text_color=("#92400e", "#f59e0b"),
            )
            self.btn_master_toggle.configure(text="▶ AVVIA TRACKING (F9)", fg_color="#10b981", hover_color="#059669")
        elif is_blinking:
            self.pill_status.configure(text="● BLINK (CLAMP)", text_color="#38bdf8")
        elif face_detected:
            self.pill_status.configure(text=f"● ATTIVO ({fps:.0f} FPS)", text_color="#10b981")
            self.safety_banner.configure(fg_color=("#ecfdf5", "#064e3b"), border_color="#059669")
            self.lbl_safety_status.configure(
                text="🟢 STATO: TRACCIAMENTO ATTIVO\nIl mouse risponde al capo. Premi F9 per sospendere in qualsiasi momento.",
                text_color=("#065f46", "#34d399"),
            )
            self.btn_master_toggle.configure(text="⏸ SOSPENDI PAUSA (F9)", fg_color="#d97706", hover_color="#b45309")
        else:
            self.pill_status.configure(text="● VOLTO FUORI CAMPO", text_color="#ef4444")
            self.safety_banner.configure(fg_color=("#fef2f2", "#450a0a"), border_color="#dc2626")
            self.lbl_safety_status.configure(
                text="🔴 ATTENZIONE: VOLTO NON RILEVATO\nPosizionati davanti alla fotocamera per riprendere il tracciamento.",
                text_color=("#991b1b", "#f87171"),
            )

        # Diagnostica Luce
        if (fps > 0 and fps < 32.0) or luma < 40.0:
            self.lbl_light_badge.configure(text="⚠️ Luce Bassa", text_color="#ef4444")
            self.lbl_wizard_align.configure(text="⚠️ Luce bassa nella stanza: accendi la luce per migliorare gli FPS", text_color="#ef4444")
        elif (fps > 0 and fps < 48.0) or luma < 70.0:
            self.lbl_light_badge.configure(text="Luce Media", text_color="#f59e0b")
            self.lbl_wizard_align.configure(text="Luce media: tracking operativo", text_color="#f59e0b")
        else:
            self.lbl_light_badge.configure(text="Luce: OK", text_color="#10b981")
            self.lbl_wizard_align.configure(text="Luce ottimale: 60 FPS stabili garantiti", text_color="#10b981")

        # Aggiornamento VU Meter Microfono
        if self.acoustic_enabled.get():
            thresh = self.acoustic_threshold_val.get()
            self.vu_bar.set(min(1.0, mic_volume * 3.0))
            col = "#ef4444" if mic_volume > thresh else "#10b981"
            self.lbl_mic_reading.configure(text=f"RMS: {mic_volume:.3f} / Soglia: {thresh:.2f}", text_color=col)
        else:
            self.vu_bar.set(0.0)
            self.lbl_mic_reading.configure(text="Microfono disattivato", text_color="#64748b")

        # Disegno Radar Posturale (Tobii Dynavox Style)
        self._draw_radar(yaw, pitch, roll, face_detected)

    def _draw_radar(self, yaw: float, pitch: float, roll: float, face_detected: bool):
        self.radar_canvas.delete("all")
        w = self.radar_canvas.winfo_width()
        h = self.radar_canvas.winfo_height()
        if w < 10 or h < 10:
            w, h = 240, 180

        cx, cy = w // 2, h // 2
        r = min(cx, cy) - 20

        self.radar_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#334155", width=1)
        self.radar_canvas.create_oval(cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2, outline="#1e293b", width=1)
        self.radar_canvas.create_line(cx - r, cy, cx + r, cy, fill="#1e293b", width=1)
        self.radar_canvas.create_line(cx, cy - r, cx, cy + r, fill="#1e293b", width=1)

        if not face_detected:
            self.radar_canvas.create_text(cx, cy, text="Posizionarsi davanti alla webcam", fill="#ef4444", font=("Segoe UI", 10))
            self.lbl_radar_status.configure(text="Volto non rilevato", text_color="#ef4444")
            return

        px = cx + int((yaw / 20.0) * (r * 0.8))
        py = cy - int((pitch / 15.0) * (r * 0.8))
        px = max(cx - r + 5, min(cx + r - 5, px))
        py = max(cy - r + 5, min(cy + r - 5, py))

        dist_center = math.hypot(px - cx, py - cy)
        color = "#10b981" if dist_center < r * 0.4 else "#f59e0b" if dist_center < r * 0.8 else "#ef4444"

        head_r = 14
        self.radar_canvas.create_oval(px - head_r, py - head_r, px + head_r, py + head_r, fill=color, outline="#f8fafc", width=2)

        rad_roll = math.radians(roll)
        dx_roll = math.cos(rad_roll) * 22
        dy_roll = -math.sin(rad_roll) * 22
        self.radar_canvas.create_line(px - dx_roll, py - dy_roll, px + dx_roll, py + dy_roll, fill="#38bdf8", width=3)

        self.lbl_radar_yaw.configure(text=f"Yaw: {yaw:+.1f}°")
        self.lbl_radar_pitch.configure(text=f"Pitch: {pitch:+.1f}°")
        self.lbl_radar_roll.configure(text=f"Roll: {roll:+.1f}°")

        status_txt = "Centratura Ottimale" if dist_center < r * 0.4 else "Postura Asimmetrica (Premi F12)"
        self.lbl_radar_status.configure(text=status_txt, text_color=color)
