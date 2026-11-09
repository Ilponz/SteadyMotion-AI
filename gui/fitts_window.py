"""
Finestra a Tutto Schermo per la Valutazione Scientifica della Legge di Fitts (ISO 9241-9).
Progettata per SteadyMotion AI v3.0 / v3.1.

Obiettivo Clinico & Riabilitativo:
- Permette a fisiatri, logopedisti e terapisti occupazionali di misurare con precisione millimetrica
  la capacità del canale informativo motorio del paziente (Throughput in bit/s) secondo la norma ISO 9241-9.
- Genera un pattern circolare a 13 o 16 bersagli con attraversamento diametrale reciproco (reciprocal star pattern).
- Fornisce un report finale dettagliato con MT (Movement Time), IDe (Indice di Difficoltà Effettivo),
  TPe (Throughput Effettivo) e Tasso di Errore.
"""

import math
import time
from typing import Any, Callable, Dict, List, Optional
import tkinter as tk
import customtkinter as ctk

from core.fitts_evaluator import FittsEvaluator, generate_iso_circle_targets

try:
    import winsound
except ImportError:
    winsound = None


class FittsAssessmentWindow(ctk.CTkToplevel):
    """Finestra modale interattiva per la somministrazione del test motorio ISO 9241-9."""

    def __init__(
        self,
        parent: tk.Tk,
        on_assessment_complete: Callable[[Dict[str, Any]], None],
        num_targets: int = 13,
        target_width: float = 70.0,
        dwell_duration: float = 0.55,
        audio_feedback: Optional[Any] = None,
    ):
        super().__init__(parent)
        self.on_assessment_complete = on_assessment_complete
        self.num_targets = int(num_targets)
        self.target_width = float(target_width)
        self.dwell_duration = float(dwell_duration)
        self.audio_feedback = audio_feedback

        self.title("Valutazione Standardizzata ISO 9241-9 — SteadyMotion AI")
        self.attributes("-fullscreen", True)
        self.configure(fg_color="#0B0F19")
        self.lift()
        self.focus_force()

        self.evaluator = FittsEvaluator()
        self.targets: List[Dict[str, Any]] = []
        self.current_target_idx: int = 0
        self.is_finished: bool = False
        self.current_dwell_progress: float = 0.0
        self.target_hover_start: Optional[float] = None
        self.last_cursor_x: float = 0.0
        self.last_cursor_y: float = 0.0

        # Canvas grafico ad alte prestazioni
        self.canvas = tk.Canvas(self, bg="#0B0F19", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Barra superiore informativa
        self.info_frame = ctk.CTkFrame(self, fg_color="#162032", corner_radius=12, border_width=1, border_color="#1E293B")
        self.info_frame.place(relx=0.5, rely=0.03, anchor="n", relwidth=0.7)

        self.step_label = ctk.CTkLabel(
            self.info_frame,
            text=f"Test Fitts ISO 9241-9: Bersaglio 1 di {self.num_targets}",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#38BDF8",
        )
        self.step_label.pack(side="left", padx=20, pady=8)

        self.btn_abort = ctk.CTkButton(
            self.info_frame,
            text="✕ Annulla Test",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#EF4444",
            hover_color="#DC2626",
            width=100,
            height=28,
            command=self.destroy,
        )
        self.btn_abort.pack(side="right", padx=15, pady=8)

        # Attendi rendering iniziale per ottenere dimensioni schermo
        self.after(50, self._init_targets_and_loop)

    def _play_chime(self, freq: int = 1000):
        if self.audio_feedback and hasattr(self.audio_feedback, "play"):
            try:
                self.audio_feedback.play("success")
                return
            except Exception:
                pass
        if winsound is not None:
            try:
                winsound.Beep(freq, 40)
            except Exception:
                pass

    def _init_targets_and_loop(self):
        w = max(600, self.canvas.winfo_width())
        h = max(500, self.canvas.winfo_height())
        cx = w / 2.0
        cy = h / 2.0
        radius = min(cx, cy) * 0.65

        self.targets = generate_iso_circle_targets(
            center_x=cx,
            center_y=cy,
            radius=radius,
            num_targets=self.num_targets,
            target_width=self.target_width,
        )
        self.current_target_idx = 0
        self.evaluator.start_trial(start_x=cx, start_y=cy, now=time.perf_counter())
        self._tick()

    def _tick(self):
        if not self.winfo_exists() or self.is_finished:
            return

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 100 or h < 100 or not self.targets:
            self.after(30, self._tick)
            return

        self.canvas.delete("all")

        # Rileva posizione attuale del puntatore mouse reale / emulato
        cur_x = float(self.winfo_pointerx())
        cur_y = float(self.winfo_pointery())
        self.last_cursor_x = cur_x
        self.last_cursor_y = cur_y

        active_t = self.targets[self.current_target_idx]
        tx, ty = active_t["x"], active_t["y"]
        tw = active_t["width"]
        tr = tw / 2.0

        # Disegna tutti i target passivi come anelli sottili
        for idx, t in enumerate(self.targets):
            if idx == self.current_target_idx:
                continue
            x, y = t["x"], t["y"]
            r = t["width"] / 2.0
            self.canvas.create_oval(x - r, y - r, x + r, y + r, outline="#1E293B", width=2)
            self.canvas.create_text(x, y, text=str(t["step"] + 1), fill="#475569", font=("Segoe UI", 10, "bold"))

        # Linea guida dal target precedente al target attivo
        prev_idx = (self.current_target_idx - 1 + len(self.targets)) % len(self.targets)
        pt = self.targets[prev_idx]
        self.canvas.create_line(pt["x"], pt["y"], tx, ty, fill="#1E293B", dash=(4, 4), width=1)

        # Controllo se il puntatore è all'interno del target attivo
        dist_to_target = math.hypot(cur_x - tx, cur_y - ty)
        is_hovering = dist_to_target <= tr
        now = time.perf_counter()

        if is_hovering:
            if self.target_hover_start is None:
                self.target_hover_start = now
            elapsed = now - self.target_hover_start
            self.current_dwell_progress = min(1.0, elapsed / self.dwell_duration)
        else:
            self.target_hover_start = None
            self.current_dwell_progress = max(0.0, self.current_dwell_progress - 0.10)

        # Disegna target attivo
        glow_color = "#10B981" if self.current_dwell_progress > 0.0 else "#38BDF8"
        self.canvas.create_oval(tx - tr, ty - tr, tx + tr, ty + tr, outline=glow_color, width=4)
        self.canvas.create_oval(tx - 6, ty - 6, tx + 6, ty + 6, fill=glow_color, outline="#FFFFFF", width=1)

        # Arco di caricamento dwell
        if self.current_dwell_progress > 0.01:
            extent = -self.current_dwell_progress * 360.0
            self.canvas.create_arc(
                tx - tr, ty - tr, tx + tr, ty + tr,
                start=90, extent=extent, outline="#22C55E", width=6, style="arc"
            )

        # Indicatore testuale
        self.canvas.create_text(
            tx, ty + tr + 18,
            text=f"{int(self.current_dwell_progress * 100)}%",
            fill="#94A3B8",
            font=("Segoe UI", 11, "bold"),
        )

        # Completamento bersaglio corrente
        if self.current_dwell_progress >= 1.0:
            self._complete_current_target(hit_x=cur_x, hit_y=cur_y)

        self.after(25, self._tick)

    def _complete_current_target(self, hit_x: float, hit_y: float):
        t = self.targets[self.current_target_idx]
        now = time.perf_counter()

        self.evaluator.record_hit(
            target_id=t["target_id"],
            target_x=t["x"],
            target_y=t["y"],
            target_width=t["width"],
            now=now,
            is_hit=True,
            hit_x=hit_x,
            hit_y=hit_y,
        )
        self._play_chime(1000 if self.current_target_idx < self.num_targets - 1 else 1300)

        self.current_target_idx += 1
        self.target_hover_start = None
        self.current_dwell_progress = 0.0

        if self.current_target_idx >= len(self.targets):
            self.is_finished = True
            self._show_summary_screen()
        else:
            self.step_label.configure(text=f"Test Fitts ISO 9241-9: Bersaglio {self.current_target_idx + 1} di {self.num_targets}")
            self.evaluator.start_trial(start_x=hit_x, start_y=hit_y, now=now)

    def _show_summary_screen(self):
        """Presenta il report riabilitativo finale con calcolo ISO 9241-9."""
        self.canvas.delete("all")
        self.info_frame.destroy()

        summary = self.evaluator.get_summary()

        report = ctk.CTkFrame(self, fg_color="#162032", corner_radius=16, border_width=1, border_color="#38BDF8")
        report.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.68, relheight=0.74)

        ctk.CTkLabel(
            report,
            text="🏆 Valutazione Clinica ISO 9241-9 Completata!",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#22C55E",
        ).pack(pady=(25, 8))

        ctk.CTkLabel(
            report,
            text="Misurazione quantitativa della capacità del canale motorio cefalico del paziente:",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#94A3B8",
        ).pack(pady=(0, 16))

        grid = ctk.CTkFrame(report, fg_color="#0F172A", corner_radius=12)
        grid.pack(fill="x", padx=35, pady=8)
        grid.grid_columnconfigure((0, 1), weight=1)

        # Colonna Sinistra
        c1 = ctk.CTkFrame(grid, fg_color="transparent")
        c1.grid(row=0, column=0, padx=20, pady=15, sticky="nsew")
        ctk.CTkLabel(c1, text="⚡ Efficienza & Throughput", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#38BDF8").pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(c1, text=f"• Throughput Nominale (TP): {summary['mean_throughput_bps']:.2f} bit/s", font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#E2E8F0").pack(anchor="w", pady=2)
        ctk.CTkLabel(c1, text=f"• Throughput Effettivo (TPe): {summary['effective_throughput_tpe']:.2f} bit/s", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color="#10B981").pack(anchor="w", pady=2)
        ctk.CTkLabel(c1, text=f"• Indice di Difficoltà (IDe): {summary['effective_index_of_difficulty_ide']:.2f} bit", font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#E2E8F0").pack(anchor="w", pady=2)

        # Colonna Destra
        c2 = ctk.CTkFrame(grid, fg_color="transparent")
        c2.grid(row=0, column=1, padx=20, pady=15, sticky="nsew")
        ctk.CTkLabel(c2, text="🎯 Accuratezza & Precisione", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="#38BDF8").pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(c2, text=f"• Tempo di Movimento (MT): {summary['mean_movement_time_sec']:.2f} s", font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#E2E8F0").pack(anchor="w", pady=2)
        ctk.CTkLabel(c2, text=f"• Dispersione Endpoint (σ): {summary['endpoint_dispersion_sigma_px']:.1f} px", font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#E2E8F0").pack(anchor="w", pady=2)
        ctk.CTkLabel(c2, text=f"• Tasso di Errore: {summary['error_rate_pct']:.1f}%", font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#E2E8F0").pack(anchor="w", pady=2)

        # Diagnosi del canale motorio
        tpe = summary['effective_throughput_tpe']
        if tpe >= 3.0:
            diag_text = "🌟 Canale Motorio Ottimale: controllo cefalico eccellente e fluidità comparabile al mouse convenzionale."
            diag_col = "#22C55E"
        elif tpe >= 1.8:
            diag_text = "✅ Canale Motorio Buono: controllo stabile idoneo all'uso quotidiano intensivo e navigazione web."
            diag_col = "#38BDF8"
        elif tpe >= 0.9:
            diag_text = "⚠️ Canale Motorio Funzionale: lieve lentezza o fatica motoria, consigliata modalità Dwell estesa o Sniper Mode."
            diag_col = "#F59E0B"
        else:
            diag_text = "🛡 Canale Motorio Ridotto: dismetria o debolezza marcata, consigliati target allargati e filtro Atassia attivo."
            diag_col = "#EF4444"

        ctk.CTkLabel(report, text=diag_text, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=diag_col, wraplength=600).pack(pady=12)

        btn_row = ctk.CTkFrame(report, fg_color="transparent")
        btn_row.pack(pady=15)

        def apply_and_close():
            self.on_assessment_complete(summary)
            self.destroy()

        ctk.CTkButton(
            btn_row,
            text="💾 Salva Risultati nella Cartella Clinica & Esci",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            height=36,
            command=apply_and_close,
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_row,
            text="🔄 Ripeti Valutazione",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#334155",
            hover_color="#475569",
            height=36,
            command=lambda: [report.destroy(), self._init_targets_and_loop()],
        ).pack(side="left", padx=10)
