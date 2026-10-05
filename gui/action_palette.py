"""
Barra Flottante dei Clic & Palette Azioni Assistive (Floating Dwell Action Palette).
Progettata specificamente per consentire a persone con grave disabilità motoria (SLA, tetraplegia)
di controllare autonomamente al 100% l'ambiente desktop Windows senza bisogno di un caregiver:
1. Sempre in Primo Piano (Topmost) a lato dello schermo, con tasti ampi per Dwell Click.
2. Selezione Modalità di Clic:
   - Clic Sinistro Standard (Left Click)
   - Clic Destro Contestuale (Right Click, one-shot con ripristino automatico a Left)
   - Doppio Clic Rapido (Double Click per aprire file e cartelle)
   - Trascina & Rilascia (Drag & Drop con blocco e sblocco visivo)
   - Scorrimento Pagina (Scroll Su / Scroll Giù per documenti e browser)
   - Modalità Riposo / Pausa (permette di guardare video o riposare gli occhi senza clic involontari)
   - Apertura Tastiera Flottante
3. Feedback Visivo LED: il pulsante attivo si illumina con colore ad alto contrasto.
"""

import tkinter as tk
from typing import Any, Callable, Dict, Optional
import customtkinter as ctk


class FloatingActionPaletteWindow(ctk.CTkToplevel):
    """Mini-barra comandi flottante sempre in primo piano per azioni del mouse assistive."""

    def __init__(
        self,
        parent: tk.Tk,
        dwell_clicker: Optional[Any] = None,
        virtual_input: Optional[Any] = None,
        on_toggle_pause: Optional[Callable[[], None]] = None,
        on_toggle_keyboard: Optional[Callable[[], None]] = None,
        on_close_callback: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.dwell_clicker = dwell_clicker
        self.virtual_input = virtual_input
        self.on_toggle_pause = on_toggle_pause
        self.on_toggle_keyboard = on_toggle_keyboard
        self.on_close_callback = on_close_callback

        self.title("Azioni Mouse — SteadyMotion AI")
        # Posiziona la barra verticale sul bordo sinistro dello schermo
        self.geometry("90x440+20+200")
        self.minsize(80, 380)
        self.attributes("-topmost", True)
        self.configure(fg_color="#0F172A")

        self.active_mode = "left"
        self.is_paused = False
        self.buttons: Dict[str, ctk.CTkButton] = {}

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # Impugnatura per trascinamento
        grip = ctk.CTkLabel(
            self,
            text="::: AZIONI :::",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color="#64748B",
            height=16,
        )
        grip.pack(fill="x", pady=(4, 2))

        # Definizione delle Azioni della Palette
        actions = [
            ("left", "👆\nSX", "Clic Sinistro (Standard)", "#10B981"),
            ("right", "✌\nDX", "Clic Destro (Menu)", "#F59E0B"),
            ("double", "🔁\n2x", "Doppio Clic (Apri)", "#38BDF8"),
            ("drag", "✊\nTRASC.", "Trascina & Rilascia", "#EF4444"),
            ("scroll_up", "🔼\nSU", "Scorri Pagina Su", "#6366F1"),
            ("scroll_down", "🔽\nGIÙ", "Scorri Pagina Giù", "#6366F1"),
            ("keyboard", "⌨\nTAST.", "Apri Tastiera", "#8B5CF6"),
            ("pause", "⏸\nPAUSA", "Sospendi Tracking / Riposo", "#E11D48"),
        ]

        for act_id, label, tooltip, active_col in actions:
            btn = ctk.CTkButton(
                self,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color="#1E293B",
                hover_color=active_col,
                border_width=1,
                border_color="#334155",
                corner_radius=6,
                height=42,
                command=lambda a=act_id: self.select_action(a),
            )
            btn.pack(fill="x", padx=4, pady=2)
            self.buttons[act_id] = btn

        self._update_button_styles()

    def select_action(self, action: str):
        """Gestisce il clic/dwell su un'azione della palette."""
        if action == "scroll_up":
            if self.virtual_input:
                try:
                    self.virtual_input.scroll(3)
                except Exception:
                    pass
            return
        elif action == "scroll_down":
            if self.virtual_input:
                try:
                    self.virtual_input.scroll(-3)
                except Exception:
                    pass
            return
        elif action == "keyboard":
            if self.on_toggle_keyboard:
                self.on_toggle_keyboard()
            return
        elif action == "pause":
            if self.on_toggle_pause:
                self.on_toggle_pause()
            return

        # Modalità mouse per dwell clicker: left, right, double, drag
        self.active_mode = action
        if self.dwell_clicker:
            self.dwell_clicker.set_action(action)

        self._update_button_styles()

    def on_click_completed(self, executed_action: str):
        """Notifica che il dwell clicker ha eseguito un clic (per ripristino modalità standard)."""
        if executed_action in ("right", "double"):
            self.active_mode = "left"
            self._update_button_styles()
        elif executed_action == "drag":
            # Se era drag, l'utente potrebbe aver agganciato o sganciato
            if self.virtual_input and not self.virtual_input.is_dragging:
                self.active_mode = "left"
            self._update_button_styles()

    def set_pause_state(self, is_paused: bool):
        """Sincronizza lo stato visivo di pausa con l'app centrale."""
        self.is_paused = is_paused
        if "pause" in self.buttons:
            if is_paused:
                self.buttons["pause"].configure(
                    text="▶\nATTIVA",
                    fg_color="#10B981",
                    hover_color="#059669",
                    border_color="#34D399",
                )
            else:
                self.buttons["pause"].configure(
                    text="⏸\nPAUSA",
                    fg_color="#1E293B",
                    hover_color="#E11D48",
                    border_color="#334155",
                )

    def _update_button_styles(self):
        """Aggiorna i colori e bordi evidenziando la modalità attiva."""
        colors = {
            "left": "#10B981",
            "right": "#F59E0B",
            "double": "#38BDF8",
            "drag": "#EF4444",
        }

        for act_id in ("left", "right", "double", "drag"):
            if act_id not in self.buttons:
                continue
            btn = self.buttons[act_id]
            if act_id == self.active_mode:
                col = colors.get(act_id, "#38BDF8")
                btn.configure(fg_color=col, border_color="#FFFFFF", border_width=2)
            else:
                btn.configure(fg_color="#1E293B", border_color="#334155", border_width=1)

    def _on_close(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()
