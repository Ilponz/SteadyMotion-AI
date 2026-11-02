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

import ctypes
import os
import threading
import tkinter as tk
from typing import Any, Callable, Dict, List, Optional, Tuple
import customtkinter as ctk

from core.word_predictor import WordPredictor
from core.phrasebook import PhrasebookManager
from core.tts_engine import TTSEngine


class FloatingKeyboardWindow(ctk.CTkToplevel):
    """Finestra flottante della tastiera assistiva con predizione di parola intelligente."""

    def __init__(
        self,
        parent: tk.Tk,
        virtual_input_controller: Optional[Any] = None,
        on_close_callback: Optional[Callable[[], None]] = None,
        clinical_logger: Optional[Any] = None,
        audio_feedback: Optional[Any] = None,
    ):
        super().__init__(parent)
        self.virtual_input = virtual_input_controller
        self.on_close_callback = on_close_callback
        self.clinical_logger = clinical_logger
        self.audio_feedback = audio_feedback

        self.title("Tastiera Assistiva Flottante — SteadyMotion AI")
        self.geometry("820x430+150+480")
        self.minsize(680, 360)
        self.attributes("-topmost", True)
        self.configure(fg_color="#0F172A")

        # Motore Sintesi Vocale Clinico Asincrono (Zero Marshalling Error)
        self.tts = TTSEngine(rate=0, volume=100)

        # Motore Predittivo Intelligente (AAC Word Predictor) & Persistenza Lessico Utente
        self.word_predictor = WordPredictor()
        self.lexicon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "user_lexicon.json"
        )
        self.word_predictor.load_user_lexicon(self.lexicon_path)
        self.sug_buttons: List[ctk.CTkButton] = []

        # Prontuario Frasi Clinico e Personalizzabile AAC
        self.phrasebook = PhrasebookManager()
        self.current_aac_category = tk.StringVar(value="BISOGNI_PRIMARI")

        self.direct_injection = tk.BooleanVar(value=True)
        self.typed_text = tk.StringVar(value="")

        self._build_ui()
        self.typed_text.trace_add("write", lambda *args: self._update_suggestions())
        self._update_suggestions()
        self._apply_noactivate_style()
        self.after(500, self._poll_foreground_target)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _apply_noactivate_style(self):
        """
        Applica lo stile Win32 WS_EX_NOACTIVATE alla finestra della tastiera.
        Impedisce categoricamente a Windows di rubare il focus all'applicazione sottostante
        (Notepad, Microsoft Word, Browser, Chat) quando l'utente clicca o effettua il Dwell
        sui tasti o sui suggerimenti predittivi.
        """
        try:
            import ctypes
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if hwnd == 0:
                hwnd = self.winfo_id()
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE)
        except Exception:
            pass

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

        # Badge di Tracciamento Focus Finestra Attiva
        self.lbl_target = ctk.CTkLabel(
            top_bar,
            text="🎯 Destinazione: Desktop",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#10B981",
        )
        self.lbl_target.pack(side="left", padx=8)

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

        # Pulsante Allarme Caregiver
        btn_alarm = ctk.CTkButton(
            top_bar,
            text="🚨 AIUTO!",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=26,
            width=75,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            command=self._handle_emergency_call,
        )
        btn_alarm.pack(side="right", padx=4)

        # Pulsante Salva nei Rapidi AAC
        btn_save = ctk.CTkButton(
            top_bar,
            text="➕ Salva nei Rapidi",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=26,
            width=120,
            fg_color="#059669",
            hover_color="#047857",
            command=self._handle_save_phrase,
        )
        btn_save.pack(side="right", padx=4)

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

        # 3. Barra Suggerimenti Predittivi (AAC Autocomplete Bar)
        sug_frame = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=8, height=36)
        sug_frame.pack(fill="x", padx=6, pady=2)

        lbl_sug = ctk.CTkLabel(
            sug_frame,
            text="✨ SUGGERIMENTI:",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#94A3B8",
        )
        lbl_sug.pack(side="left", padx=(8, 4))

        self.sug_buttons = []
        for i in range(4):
            btn = ctk.CTkButton(
                sug_frame,
                text="",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                height=28,
                fg_color="#0B0F19",
                border_width=1,
                border_color="#334155",
                hover_color="#0284C7",
                text_color="#38BDF8",
                state="disabled",
            )
            btn.pack(side="left", expand=True, fill="both", padx=3, pady=3)
            self.sug_buttons.append(btn)

        # 4. Schede Layout (Lettere, Simboli, Frasi Rapide)
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
        """Costruisce la scheda Prontuario Frasi AAC con selettore categorie e griglia dinamica."""
        # 1. Barra di selezione categoria
        cat_bar = ctk.CTkFrame(self.tab_aac, fg_color="transparent")
        cat_bar.pack(fill="x", padx=4, pady=(2, 4))

        categories = self.phrasebook.get_categories()
        cat_labels = {
            "BISOGNI_PRIMARI": "🚨 Bisogni",
            "SALUTE_ASSISTENZA": "🩺 Assistenza",
            "COMUNICAZIONE_SOCIALE": "💬 Sociale",
            "POSTURA_COMFORT": "🛏 Comfort",
        }
        self._cat_display_map = cat_labels

        display_values = [cat_labels.get(c, c) for c in categories]
        initial_val = cat_labels.get(self.current_aac_category.get(), self.current_aac_category.get())

        self.cat_segmented = ctk.CTkSegmentedButton(
            cat_bar,
            values=display_values,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            selected_color="#6366F1",
            selected_hover_color="#4F46E5",
            unselected_color="#1E293B",
            unselected_hover_color="#334155",
            command=self._on_aac_category_changed,
        )
        self.cat_segmented.set(initial_val)
        self.cat_segmented.pack(fill="x", expand=True)

        # 2. Contenitore griglia pulsanti frasi
        self.aac_grid_frame = ctk.CTkFrame(self.tab_aac, fg_color="transparent")
        self.aac_grid_frame.pack(fill="both", expand=True, padx=4, pady=2)

        self._render_aac_phrases()

    def _on_aac_category_changed(self, display_name: str):
        """Gestisce il cambio categoria AAC."""
        for cat_key, d_name in self._cat_display_map.items():
            if d_name == display_name:
                self.current_aac_category.set(cat_key)
                break
        else:
            self.current_aac_category.set(display_name)
        self._render_aac_phrases()

    def _render_aac_phrases(self):
        """Rigenera la griglia dei pulsanti per la categoria attiva."""
        for widget in self.aac_grid_frame.winfo_children():
            widget.destroy()

        cat = self.current_aac_category.get()
        phrases = self.phrasebook.get_phrases(cat)
        if not phrases:
            lbl = ctk.CTkLabel(
                self.aac_grid_frame,
                text="Nessuna frase disponibile in questa categoria.",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color="#94A3B8",
            )
            lbl.pack(expand=True)
            return

        cols = 3
        for idx, phrase in enumerate(phrases):
            r = idx // cols
            c = idx % cols
            btn = ctk.CTkButton(
                self.aac_grid_frame,
                text=phrase,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                fg_color="#1E293B",
                hover_color="#8B5CF6",
                height=40,
                command=lambda p=phrase: self._handle_phrase_click(p),
            )
            btn.bind("<Button-3>", lambda e, p=phrase, c=cat: self._handle_phrase_right_click(c, p))
            btn.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")
            self.aac_grid_frame.grid_columnconfigure(c, weight=1)
            self.aac_grid_frame.grid_rowconfigure(r, weight=1)

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

        # 3. Registrazione per telemetria clinica CAA
        if self.clinical_logger is not None:
            try:
                self.clinical_logger.record_typing(1)
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

    def _handle_save_phrase(self):
        """Salva il testo digitato nei prontuari rapidi AAC della categoria attiva."""
        text = self.typed_text.get().strip()
        if not text:
            return
        cat = self.current_aac_category.get() or "COMUNICAZIONE_SOCIALE"
        success = self.phrasebook.add_phrase(cat, text)
        if success:
            self._render_aac_phrases()
            self.word_predictor.learn_word(text)
            try:
                if hasattr(self, "lexicon_path") and self.lexicon_path:
                    self.word_predictor.save_user_lexicon(self.lexicon_path)
            except Exception:
                pass
            if self.audio_feedback:
                self.audio_feedback.play("success")
            try:
                self.tabview.set("💬 Frasi Rapide Assistive")
            except Exception:
                pass

    def _handle_phrase_right_click(self, category: str, phrase: str):
        """Elimina una frase con clic destro (funzione Caregiver)."""
        removed = self.phrasebook.remove_phrase(category, phrase)
        if removed:
            self._render_aac_phrases()
            if self.audio_feedback:
                self.audio_feedback.play("click")

    def _handle_phrase_click(self, phrase: str):
        self.typed_text.set(phrase)
        if self.direct_injection.get() and self.virtual_input:
            try:
                self.virtual_input.send_unicode_char(phrase + " ")
            except Exception:
                pass
        # Apprendi frase nel dizionario predittivo
        self.word_predictor.learn_word(phrase)
        try:
            if hasattr(self, "lexicon_path") and self.lexicon_path:
                self.word_predictor.save_user_lexicon(self.lexicon_path)
        except Exception:
            pass
        # Verbalizza subito con sintesi vocale
        self._speak_phrase(phrase)
        # Registrazione per telemetria clinica CAA (frase predefinita)
        if self.clinical_logger is not None:
            try:
                self.clinical_logger.record_prediction_used(phrase, prefix_len=0)
            except Exception:
                pass

    def _extract_current_prefix_and_previous(self) -> Tuple[str, Optional[str]]:
        """Estrae l'ultimo token non completato e la parola precedente completata."""
        text = self.typed_text.get()
        if not text:
            return "", None
        tokens = text.split()
        if text[-1].isspace():
            # Il cursore è dopo uno spazio: prefisso vuoto, l'ultimo token è la parola precedente
            prev = tokens[-1] if tokens else None
            return "", prev
        else:
            # Si sta digitando una parola
            prefix = tokens[-1] if tokens else ""
            prev = tokens[-2] if len(tokens) >= 2 else None
            return prefix, prev

    def _extract_current_prefix(self) -> str:
        prefix, _ = self._extract_current_prefix_and_previous()
        return prefix

    def _update_suggestions(self):
        """Aggiorna i 4 pulsanti di predizione rapida con supporto Next-Word Bigrammi."""
        if not hasattr(self, "sug_buttons") or not self.sug_buttons:
            return
        prefix, prev_word = self._extract_current_prefix_and_previous()
        suggestions = self.word_predictor.predict(prefix, previous_word=prev_word, max_results=4)

        for i, btn in enumerate(self.sug_buttons):
            if i < len(suggestions):
                word = suggestions[i]
                btn.configure(
                    text=word,
                    state="normal",
                    fg_color="#1E293B",
                    text_color="#38BDF8",
                    command=lambda w=word: self._handle_suggestion_click(w),
                )
            else:
                btn.configure(
                    text="·",
                    state="disabled",
                    fg_color="#0B0F19",
                    text_color="#334155",
                    command=lambda: None,
                )

    def _handle_suggestion_click(self, suggestion: str):
        """Completa istantaneamente la parola, riducendo del 60-80% i dwell click necessari."""
        if not suggestion:
            return

        prefix, prev_word = self._extract_current_prefix_and_previous()
        cur = self.typed_text.get()

        # Calcolo del testo sostituito e iniezione diretta sincronizzata
        if prefix:
            if suggestion.upper().startswith(prefix.upper()):
                remainder = suggestion[len(prefix):] + " "
                new_text = cur[:-len(prefix)] + suggestion + " "
                if self.direct_injection.get() and self.virtual_input:
                    try:
                        self.virtual_input.send_unicode_char(remainder)
                    except Exception:
                        pass
            else:
                # Espansione di abbreviazione AAC (es. 'tvb' -> 'TI VOGLIO BENE')
                new_text = cur[:-len(prefix)] + suggestion + " "
                if self.direct_injection.get() and self.virtual_input:
                    try:
                        for _ in range(len(prefix)):
                            self.virtual_input.send_key_event(0x08)  # VK_BACK
                        self.virtual_input.send_unicode_char(suggestion + " ")
                    except Exception:
                        pass
        else:
            remainder = suggestion + " "
            new_text = cur + (" " if cur and not cur.endswith(" ") else "") + suggestion + " "
            if self.direct_injection.get() and self.virtual_input:
                try:
                    self.virtual_input.send_unicode_char(remainder)
                except Exception:
                    pass

        self.typed_text.set(new_text)

        # Apprendimento adattivo in RAM (sia vocabolo che bigramma contestuale) e persistenza su disco
        if prev_word:
            self.word_predictor.learn_bigram(prev_word, suggestion)
        self.word_predictor.learn_word(suggestion)
        try:
            if hasattr(self, "lexicon_path") and self.lexicon_path:
                self.word_predictor.save_user_lexicon(self.lexicon_path)
        except Exception:
            pass

        # Registrazione per telemetria clinica CAA
        if self.clinical_logger is not None:
            try:
                self.clinical_logger.record_prediction_used(suggestion, prefix_len=len(prefix))
            except Exception:
                pass

        # Cursore grafico alla fine del display
        try:
            self.display_entry.icursor(tk.END)
        except Exception:
            pass

    def _handle_emergency_call(self):
        """Attiva l'allarme urgente per chiamare il caregiver e verbalizza la richiesta di soccorso."""
        self.typed_text.set("AIUTO SUBITO!")
        if hasattr(self, "audio_feedback") and self.audio_feedback is not None:
            try:
                self.audio_feedback.play_alarm()
            except Exception:
                pass
        if hasattr(self, "clinical_logger") and self.clinical_logger is not None:
            try:
                self.clinical_logger.record_emergency_call()
            except Exception:
                pass
        self._speak_phrase("Attenzione! Richiesta di aiuto immediato! Vieni qui per favore!")

    def _poll_foreground_target(self):
        """Verifica periodicamente quale finestra esterna ha il focus per informare il paziente."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd:
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.strip()
                    if title and not any(k in title for k in ("SteadyMotion", "TASTIERA ASSISTIVA")):
                        disp = title if len(title) <= 22 else title[:19] + "..."
                        self.lbl_target.configure(text=f"🎯 {disp}", text_color="#10B981")
                    elif any(k in title for k in ("SteadyMotion", "TASTIERA ASSISTIVA")):
                        pass
                    else:
                        self.lbl_target.configure(text="🎯 Desktop", text_color="#94A3B8")
        except Exception:
            pass
        try:
            if self.winfo_exists():
                self.after(500, self._poll_foreground_target)
        except Exception:
            pass

    def _speak_text(self):
        text = self.typed_text.get().strip()
        if text:
            self._speak_phrase(text)

    def _speak_phrase(self, text: str):
        if hasattr(self, "tts") and self.tts:
            self.tts.speak(text, interrupt=True)

    def _on_close(self):
        try:
            if hasattr(self, "lexicon_path") and self.lexicon_path:
                self.word_predictor.save_user_lexicon(self.lexicon_path)
        except Exception:
            pass
        if hasattr(self, "tts") and self.tts:
            self.tts.stop()
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()
