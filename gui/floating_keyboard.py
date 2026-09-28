"""
Tastiera Assistiva Flottante a Schermo (Floating Dwell On-Screen Keyboard).
Progettata specificamente per pazienti con disabilità motorie gravi:
1. Sempre in primo piano (Topmost) su tutte le finestre di Windows (Browser, Word, Notepad, Chat).
2. Tasti ampi ad alto contrasto per facilitare il puntamento cefalico e il Dwell Clicker.
3. Modalità 'Iniezione Diretta a Windows' tramite Win32 SendInput a livello kernel:
   scrive direttamente nel campo di testo attivo dell'applicazione sottostante senza blocchi UIPI.
4. Sintesi Vocale Integrata (TTS SAPI nativo) per verbalizzare parole o bisogni istantaneamente.
5. Layout QWERTY, Simboli & Numeri, e Scheda Frasi Rapide AAC.
"""

import os
import threading
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional
import customtkinter as ctk

try:
    import win32com.client
    HAS_SAPI = True
except Exception:
    HAS_SAPI = False


class FloatingKeyboardWindow(ctk.CTkToplevel):
    """Finestra flottante della tastiera assistiva."""

    def __init__(
        self,
        parent: tk.Tk,
        virtual_input_controller: Optional[Any] = None,
        on_close_callback: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.virtual_input = virtual_input_controller
        self.on_close_callback = on_close_callback

        self.title("Tastiera Assistiva Flottante — SteadyMotion AI")
        self.geometry("780x380+150+550")
        self.minsize(620, 320)
        self.attributes("-topmost", True)
        self.configure(fg_color="#0F172A")

        # Motore Sintesi Vocale
        self.speaker = None
        if HAS_SAPI:
            try:
                self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
            except Exception:
                self.speaker = None

        self.direct_injection = tk.BooleanVar(value=True)
        self.typed_text = tk.StringVar(value="")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # 1. Barra Superiore di Controllo
        top_bar = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=8)
        top_bar.pack(fill="x", padx=6, pady=(6, 2))

        lbl_title = ctk.CTkLabel(
            top_bar,
            text="⌨️ TASTIERA ASSISTIVA",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#38BDF8",
        )
        lbl_title.pack(side="left", padx=8)

        # Switch Digitazione Diretta a Windows
        sw_inject = ctk.CTkSwitch(
            top_bar,
            text="Invia a Windows (Digitazione Diretta)",
            variable=self.direct_injection,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#CBD5E1",
            progress_color="#10B981",
        )
        sw_inject.pack(side="left", padx=10)

        # Pulsante Sintesi Vocale
        btn_tts = ctk.CTkButton(
            top_bar,
            text="🔊 Parla (TTS)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=26,
            width=90,
            fg_color="#8B5CF6",
            hover_color="#7C3AED",
            command=self._speak_text,
        )
        btn_tts.pack(side="right", padx=4)

        # Pulsante Cancella Tutto
        btn_clear = ctk.CTkButton(
            top_bar,
            text="🗑 Svuota",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            height=26,
            width=65,
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self.typed_text.set(""),
        )
        btn_clear.pack(side="right", padx=4)

        # 2. Display Anteprima Testo Digitato
        text_frame = ctk.CTkFrame(self, fg_color="#0B0F19", corner_radius=8, border_width=1, border_color="#334155")
        text_frame.pack(fill="x", padx=6, pady=2)

        self.display_entry = ctk.CTkEntry(
            text_frame,
            textvariable=self.typed_text,
            font=ctk.CTkFont(family="Segoe UI", size=16),
            height=36,
            fg_color="transparent",
            border_width=0,
            text_color="#F8FAFC",
            placeholder_text="Digita con lo sguardo / capo... Il testo appare qui e viene inviato a Windows",
        )
        self.display_entry.pack(fill="x", padx=8, pady=2)

        # 3. Schede Layout (Lettere, Simboli, Frasi Rapide)
        self.tabview = ctk.CTkTabview(self, fg_color="#162032")
        self.tabview.pack(fill="both", expand=True, padx=6, pady=(2, 6))

        self.tab_letters = self.tabview.add("🔤 Lettere QWERTY")
        self.tab_symbols = self.tabview.add("🔢 Numeri & Simboli")
        self.tab_aac = self.tabview.add("💬 Frasi Rapide Assistive")

        self._build_qwerty_tab()
        self._build_symbols_tab()
        self._build_aac_tab()

    def _build_qwerty_tab(self):
        rows = [
            ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
            ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
            ["Z", "X", "C", "V", "B", "N", "M"],
        ]

        for r_idx, row in enumerate(rows):
            f_row = ctk.CTkFrame(self.tab_letters, fg_color="transparent")
            f_row.pack(fill="x", expand=True, pady=1)
            for char in row:
                btn = ctk.CTkButton(
                    f_row,
                    text=char,
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                    fg_color="#1E293B",
                    hover_color="#0284C7",
                    corner_radius=6,
                    height=38,
                    command=lambda c=char: self._handle_char_click(c),
                )
                btn.pack(side="left", expand=True, fill="both", padx=1)

        # Riga Funzioni: Spazio, Backspace, Invio
        f_func = ctk.CTkFrame(self.tab_letters, fg_color="transparent")
        f_func.pack(fill="x", expand=True, pady=1)

        btn_spc = ctk.CTkButton(
            f_func,
            text="␣ SPAZIO",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#334155",
            hover_color="#0284C7",
            height=38,
            command=lambda: self._handle_char_click(" "),
        )
        btn_spc.pack(side="left", expand=True, fill="both", padx=2)

        btn_bksp = ctk.CTkButton(
            f_func,
            text="⌫ CANC",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#DC2626",
            hover_color="#B91C1C",
            height=38,
            width=110,
            command=self._handle_backspace,
        )
        btn_bksp.pack(side="left", fill="both", padx=2)

        btn_enter = ctk.CTkButton(
            f_func,
            text="↵ INVIO",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            height=38,
            width=110,
            command=self._handle_enter,
        )
        btn_enter.pack(side="left", fill="both", padx=2)

    def _build_symbols_tab(self):
        rows = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
            [".", ",", ":", ";", "?", "!", "-", "_", "@", "/"],
            ["+", "*", "=", "%", "(", ")", "\"", "'", "<", ">"],
        ]

        for row in rows:
            f_row = ctk.CTkFrame(self.tab_symbols, fg_color="transparent")
            f_row.pack(fill="x", expand=True, pady=1)
            for char in row:
                btn = ctk.CTkButton(
                    f_row,
                    text=char,
                    font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                    fg_color="#1E293B",
                    hover_color="#0284C7",
                    corner_radius=6,
                    height=38,
                    command=lambda c=char: self._handle_char_click(c),
                )
                btn.pack(side="left", expand=True, fill="both", padx=1)

        # Riga Funzioni Simboli
        f_func = ctk.CTkFrame(self.tab_symbols, fg_color="transparent")
        f_func.pack(fill="x", expand=True, pady=1)

        btn_spc = ctk.CTkButton(
            f_func,
            text="␣ SPAZIO",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#334155",
            hover_color="#0284C7",
            height=38,
            command=lambda: self._handle_char_click(" "),
        )
        btn_spc.pack(side="left", expand=True, fill="both", padx=2)

        btn_bksp = ctk.CTkButton(
            f_func,
            text="⌫ CANC",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#DC2626",
            hover_color="#B91C1C",
            height=38,
            width=110,
            command=self._handle_backspace,
        )
        btn_bksp.pack(side="left", fill="both", padx=2)

    def _build_aac_tab(self):
        phrases = [
            "SÌ", "NO", "AIUTO!",
            "HO SETE", "HO FAME", "GRAZIE",
            "CHIAMAMI", "HO DOLORE", "ASPETTA",
            "HO FREDDO", "HO CALDO", "VOGLIO DORMIRE"
        ]

        grid = ctk.CTkFrame(self.tab_aac, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=4, pady=4)

        cols = 3
        for idx, phrase in enumerate(phrases):
            r = idx // cols
            c = idx % cols
            btn = ctk.CTkButton(
                grid,
                text=phrase,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                fg_color="#1E293B",
                hover_color="#8B5CF6",
                height=42,
                command=lambda p=phrase: self._handle_phrase_click(p),
            )
            btn.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")
            grid.grid_columnconfigure(c, weight=1)
            grid.grid_rowconfigure(r, weight=1)

    def _handle_char_click(self, char: str):
        # 1. Aggiorna buffer locale
        cur = self.typed_text.get()
        self.typed_text.set(cur + char)

        # 2. Iniezione diretta a Windows se attiva
        if self.direct_injection.get() and self.virtual_input:
            try:
                self.virtual_input.send_unicode_char(char)
            except Exception:
                pass

    def _handle_backspace(self):
        cur = self.typed_text.get()
        if cur:
            self.typed_text.set(cur[:-1])

        if self.direct_injection.get() and self.virtual_input:
            try:
                # VK_BACK = 0x08
                self.virtual_input.send_key_event(0x08)
            except Exception:
                pass

    def _handle_enter(self):
        cur = self.typed_text.get()
        self.typed_text.set(cur + "\n")

        if self.direct_injection.get() and self.virtual_input:
            try:
                # VK_RETURN = 0x0D
                self.virtual_input.send_key_event(0x0D)
            except Exception:
                pass

    def _handle_phrase_click(self, phrase: str):
        self.typed_text.set(phrase)
        if self.direct_injection.get() and self.virtual_input:
            try:
                self.virtual_input.send_unicode_char(phrase + " ")
            except Exception:
                pass
        # Verbalizza subito con sintesi vocale
        self._speak_phrase(phrase)

    def _speak_text(self):
        text = self.typed_text.get().strip()
        if text:
            self._speak_phrase(text)

    def _speak_phrase(self, text: str):
        if not self.speaker:
            return

        def _worker():
            try:
                self.speaker.Speak(text)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True, name="TTSThread").start()

    def _on_close(self):
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()
