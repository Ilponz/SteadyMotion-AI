"""
Modulo di Calibrazione Clinica Range of Motion (ROM a 5 Punti).
Progettato per pazienti con mobilità cervicale ridotta o asimmetrica (SLA, distonie, tetraparesi).

Fasi operative:
1. Target 1: Centro (Neutral Reference)
2. Target 2: Alto-Sinistra (Top-Left)
3. Target 3: Alto-Destra (Top-Right)
4. Target 4: Basso-Destra (Bottom-Right)
5. Target 5: Basso-Sinistra (Bottom-Left)

Calcola automaticamente i guadagni asimmetrici per quadrante (SX, DX, SU, GIÙ)
permettendo al paziente di raggiungere tutti gli angoli dello schermo senza sforzo muscolare.
"""

import math
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import tkinter as tk
import customtkinter as ctk

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False


class CalibrationWindow(ctk.CTkToplevel):
    """
    Finestra modale a schermo intero per la calibrazione guidata a 5 punti.
    """

    TARGETS = [
        {"name": "Centro (Neutro)", "relx": 0.50, "rely": 0.50, "instr": "Guarda il centro dello schermo in posizione rilassata"},
        {"name": "Alto - Sinistra", "relx": 0.15, "rely": 0.15, "instr": "Ruota delicatamente la testa verso l'angolo in alto a sinistra"},
        {"name": "Alto - Destra", "relx": 0.85, "rely": 0.15, "instr": "Ruota la testa verso l'angolo in alto a destra"},
        {"name": "Basso - Destra", "relx": 0.85, "rely": 0.85, "instr": "Inclina la testa verso il basso a destra"},
        {"name": "Basso - Sinistra", "relx": 0.15, "rely": 0.85, "instr": "Inclina la testa verso il basso a sinistra"},
    ]

    def __init__(
        self,
        parent: tk.Tk,
        pose_provider: Callable[[], Dict[str, Any]],
        on_calibration_complete: Callable[[Dict[str, float], Dict[str, Any]], None],
    ):
        super().__init__(parent)
        self.pose_provider = pose_provider
        self.on_calibration_complete = on_calibration_complete

        self.title("Calibrazione Clinica ROM (5 Punti) — SteadyMotion AI")
        self.attributes("-fullscreen", True)
        self.configure(fg_color="#0B0F19")
        self.lift()
        self.focus_force()

        # Stato di avanzamento
        self.current_step = 0
        self.step_start_time = time.perf_counter()
        self.dwell_duration = 1.4  # Secondi di sosta stazionaria per punto
        self.samples: List[Dict[str, float]] = []
        self.point_results: List[Dict[str, float]] = []
        self.is_finished = False

        # Canvas a tutto schermo per grafica e animazione ad alto contrasto
        self.canvas = tk.Canvas(self, bg="#0B0F19", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Barra superiore informativa
        self.info_frame = ctk.CTkFrame(self, fg_color="#162032", corner_radius=12, border_width=1, border_color="#1E293B")
        self.info_frame.place(relx=0.5, rely=0.04, anchor="n", relwidth=0.7)

        self.step_label = ctk.CTkLabel(
            self.info_frame,
            text="Calibrazione Punto 1 di 5: Centro",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#38BDF8",
        )
        self.step_label.pack(pady=(10, 2))

        self.instr_label = ctk.CTkLabel(
            self.info_frame,
            text=self.TARGETS[0]["instr"],
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color="#CBD5E1",
        )
        self.instr_label.pack(pady=(0, 10))

        # Tasti di aiuto Caregiver in basso
        self.bottom_bar = ctk.CTkLabel(
            self,
            text="[Esc] Annulla ed Esci   |   [Spazio] / [Invio] Valida Punto Manualmente (Caregiver)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#64748B",
            fg_color="#0F172A",
            corner_radius=8,
            padx=16,
            pady=6,
        )
        self.bottom_bar.place(relx=0.5, rely=0.96, anchor="s")

        # Bind tastiera
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<space>", lambda e: self._advance_manual())
        self.bind("<Return>", lambda e: self._advance_manual())
        self.canvas.bind("<Button-1>", lambda e: self._advance_manual())

        # Loop di animazione e sampling a 40 Hz
        self.anim_phase = 0.0
        self.after(25, self._tick_calibration)

    def _play_chime(self, freq: int = 880):
        if HAS_WINSOUND:
            try:
                winsound.Beep(freq, 70)
            except Exception:
                pass

    def _advance_manual(self):
        """Avanza al punto successivo tramite intervento manuale dell'operatore o click."""
        if self.is_finished:
            return
        self._complete_step()

    def _complete_step(self):
        # Calcola media dei campioni registrati per il target corrente
        if not self.samples:
            pose = self.pose_provider()
            self.samples.append(pose)

        avg_raw_x = float(sum(s.get("raw_x", 0.5) for s in self.samples) / len(self.samples))
        avg_raw_y = float(sum(s.get("raw_y", 0.5) for s in self.samples) / len(self.samples))
        avg_yaw = float(sum(s.get("yaw", 0.0) for s in self.samples) / len(self.samples))
        avg_pitch = float(sum(s.get("pitch", 0.0) for s in self.samples) / len(self.samples))

        self.point_results.append({
            "target": self.TARGETS[self.current_step]["name"],
            "raw_x": avg_raw_x,
            "raw_y": avg_raw_y,
            "yaw": avg_yaw,
            "pitch": avg_pitch,
        })

        self._play_chime(880 if self.current_step < 4 else 1175)

        self.current_step += 1
        self.samples = []
        self.step_start_time = time.perf_counter()

        if self.current_step >= len(self.TARGETS):
            self.is_finished = True
            self._show_summary_screen()
        else:
            t = self.TARGETS[self.current_step]
            self.step_label.configure(text=f"Calibrazione Punto {self.current_step + 1} di 5: {t['name']}")
            self.instr_label.configure(text=t["instr"])

    def _tick_calibration(self):
        if not self.winfo_exists() or self.is_finished:
            return

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        if w > 50 and h > 50:
            self.canvas.delete("all")
            target = self.TARGETS[self.current_step]
            tx = target["relx"] * w
            ty = target["rely"] * h

            # Legge la postura attuale del capo
            pose = self.pose_provider()
            if pose.get("face_detected", True):
                self.samples.append(pose)

            # Calcolo avanzamento dwell temporizzato
            elapsed = time.perf_counter() - self.step_start_time
            prog = min(1.0, elapsed / self.dwell_duration)

            self.anim_phase += 0.12
            pulse = math.sin(self.anim_phase) * 6.0

            # Disegna mirino e anello di progresso
            r_outer = 48.0 + pulse
            r_inner = 14.0

            # Linee a croce guida
            self.canvas.create_line(tx - r_outer - 15, ty, tx - r_inner - 2, ty, fill="#38BDF8", width=2)
            self.canvas.create_line(tx + r_inner + 2, ty, tx + r_outer + 15, ty, fill="#38BDF8", width=2)
            self.canvas.create_line(tx, ty - r_outer - 15, tx, ty - r_inner - 2, fill="#38BDF8", width=2)
            self.canvas.create_line(tx, ty + r_inner + 2, tx, ty + r_outer + 15, fill="#38BDF8", width=2)

            # Cerchio esterno soffuso
            self.canvas.create_oval(tx - r_outer, ty - r_outer, tx + r_outer, ty + r_outer, outline="#1E293B", width=4)

            # Arco di caricamento progresso Dwell
            if prog > 0.01:
                extent = -prog * 360.0
                self.canvas.create_arc(
                    tx - r_outer, ty - r_outer, tx + r_outer, ty + r_outer,
                    start=90, extent=extent, outline="#22C55E", width=5, style="arc"
                )

            # Punto focale centrale ad alta luminosità
            dot_color = "#22C55E" if prog > 0.8 else "#38BDF8"
            self.canvas.create_oval(tx - r_inner, ty - r_inner, tx + r_inner, ty + r_inner, fill=dot_color, outline="#FFFFFF", width=2)

            # Testo percentuale
            self.canvas.create_text(
                tx, ty + r_outer + 24,
                text=f"{int(prog * 100)}%",
                fill="#94A3B8",
                font=("Segoe UI", 12, "bold"),
            )

            # Se il tempo è completato con successo
            if prog >= 1.0:
                self._complete_step()

        self.after(25, self._tick_calibration)

    def _show_summary_screen(self):
        """Calcola i guadagni asimmetrici e mostra il report clinico finale."""
        self.canvas.delete("all")
        self.info_frame.destroy()
        self.bottom_bar.destroy()

        p_ctr = self.point_results[0]
        p_tl = self.point_results[1]
        p_tr = self.point_results[2]
        p_br = self.point_results[3]
        p_bl = self.point_results[4]

        # Escursione differenziale normalizzata grezza rispetto al centro
        dx_left = max(0.02, abs(p_ctr["raw_x"] - (p_tl["raw_x"] + p_bl["raw_x"]) / 2.0))
        dx_right = max(0.02, abs((p_tr["raw_x"] + p_br["raw_x"]) / 2.0 - p_ctr["raw_x"]))
        dy_up = max(0.02, abs(p_ctr["raw_y"] - (p_tl["raw_y"] + p_tr["raw_y"]) / 2.0))
        dy_down = max(0.02, abs((p_bl["raw_y"] + p_br["raw_y"]) / 2.0 - p_ctr["raw_y"]))

        # Escursione angolare in gradi
        yaw_left_deg = abs(p_ctr["yaw"] - (p_tl["yaw"] + p_bl["yaw"]) / 2.0)
        yaw_right_deg = abs((p_tr["yaw"] + p_br["yaw"]) / 2.0 - p_ctr["yaw"])
        pitch_up_deg = abs(p_ctr["pitch"] - (p_tl["pitch"] + p_tr["pitch"]) / 2.0)
        pitch_down_deg = abs((p_bl["pitch"] + p_br["pitch"]) / 2.0 - p_ctr["pitch"])

        def compute_gain(dx):
            g = 0.35 / dx
            return max(1.2, min(6.5, round(g, 2)))

        gain_left = compute_gain(dx_left)
        gain_right = compute_gain(dx_right)
        gain_up = compute_gain(dy_up)
        gain_down = compute_gain(dy_down)

        gains = {
            "gain_x_left": gain_left,
            "gain_x_right": gain_right,
            "gain_y_up": gain_up,
            "gain_y_down": gain_down,
        }

        rom_stats = {
            "yaw_left_deg": round(yaw_left_deg, 1),
            "yaw_right_deg": round(yaw_right_deg, 1),
            "pitch_up_deg": round(pitch_up_deg, 1),
            "pitch_down_deg": round(pitch_down_deg, 1),
            "dx_left": round(dx_left, 4),
            "dx_right": round(dx_right, 4),
            "dy_up": round(dy_up, 4),
            "dy_down": round(dy_down, 4),
        }

        # Frame centrale del report
        report_frame = ctk.CTkFrame(self, fg_color="#162032", corner_radius=16, border_width=1, border_color="#38BDF8")
        report_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.68, relheight=0.74)

        title = ctk.CTkLabel(
            report_frame,
            text="🎉 Calibrazione ROM a 5 Punti Completata con Successo!",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#22C55E",
        )
        title.pack(pady=(25, 10))

        sub = ctk.CTkLabel(
            report_frame,
            text="L'algoritmo ha mappato l'escursione cervicale del paziente ed ha calcolato i guadagni compensativi per quadrante:",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color="#94A3B8",
            wraplength=650,
        )
        sub.pack(pady=(0, 20))

        # Card griglia valori
        grid_frame = ctk.CTkFrame(report_frame, fg_color="#0F172A", corner_radius=12)
        grid_frame.pack(fill="x", padx=40, pady=10)
        grid_frame.grid_columnconfigure((0, 1), weight=1)

        # Sinistra / Destra
        col_x = ctk.CTkFrame(grid_frame, fg_color="transparent")
        col_x.grid(row=0, column=0, padx=20, pady=15, sticky="nsew")

        ctk.CTkLabel(col_x, text="↔️ Escursione Orizzontale (Yaw)", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#38BDF8").pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(col_x, text=f"• Verso Sinistra: {yaw_left_deg:.1f}°  →  Guadagno: {gain_left:.2f}x", font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#E2E8F0").pack(anchor="w", pady=2)
        ctk.CTkLabel(col_x, text=f"• Verso Destra:  {yaw_right_deg:.1f}°  →  Guadagno: {gain_right:.2f}x", font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#E2E8F0").pack(anchor="w", pady=2)

        # Alto / Basso
        col_y = ctk.CTkFrame(grid_frame, fg_color="transparent")
        col_y.grid(row=0, column=1, padx=20, pady=15, sticky="nsew")

        ctk.CTkLabel(col_y, text="↕️ Escursione Verticale (Pitch)", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="#38BDF8").pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(col_y, text=f"• Verso l'Alto:  {pitch_up_deg:.1f}°  →  Guadagno: {gain_up:.2f}x", font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#E2E8F0").pack(anchor="w", pady=2)
        ctk.CTkLabel(col_y, text=f"• Verso il Basso: {pitch_down_deg:.1f}°  →  Guadagno: {gain_down:.2f}x", font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#E2E8F0").pack(anchor="w", pady=2)

        asym_x = abs(gain_left - gain_right)
        asym_y = abs(gain_up - gain_down)
        if asym_x > 0.5 or asym_y > 0.5:
            diag_text = "⚠️ Asimmetria Cervicale Rilevata: i quadranti asimmetrici sono stati compensati per prevenire affaticamento muscolare."
            diag_color = "#F59E0B"
        else:
            diag_text = "✅ Mobilità Simmetrica ed Equilibrata: risposta uniforme su tutti i 4 quadranti dello schermo."
            diag_color = "#22C55E"

        diag_label = ctk.CTkLabel(
            report_frame,
            text=diag_text,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=diag_color,
            wraplength=650,
        )
        diag_label.pack(pady=15)

        btn_frame = ctk.CTkFrame(report_frame, fg_color="transparent")
        btn_frame.pack(pady=20)

        def apply_and_exit():
            self.on_calibration_complete(gains, rom_stats)
            self.destroy()

        def restart():
            report_frame.destroy()
            self.current_step = 0
            self.point_results = []
            self.samples = []
            self.is_finished = False
            self.step_start_time = time.perf_counter()
            self.__init__(self.master, self.pose_provider, self.on_calibration_complete)

        btn_apply = ctk.CTkButton(
            btn_frame,
            text="💾 Applica Guadagni e Salva",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color="#22C55E",
            hover_color="#16A34A",
            text_color="#FFFFFF",
            width=220,
            height=42,
            command=apply_and_exit,
        )
        btn_apply.pack(side="left", padx=10)

        btn_repeat = ctk.CTkButton(
            btn_frame,
            text="🔄 Ripeti Calibrazione",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            fg_color="#334155",
            hover_color="#475569",
            text_color="#FFFFFF",
            width=160,
            height=42,
            command=restart,
        )
        btn_repeat.pack(side="left", padx=10)

        btn_close = ctk.CTkButton(
            btn_frame,
            text="Chiudi",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            fg_color="#1E293B",
            hover_color="#334155",
            text_color="#94A3B8",
            width=100,
            height=42,
            command=self.destroy,
        )
        btn_close.pack(side="left", padx=10)
