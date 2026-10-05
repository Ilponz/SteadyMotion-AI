"""
Finestra Grafica di Diagnostica Hardware Pre-Collaudo per Caregiver e Clinici.
Mostra in tempo reale lo stato dei sensori webcam, FPS reali, luce ambientale,
microfoni e fornisce consigli pratici per massimizzare le prestazioni.
"""

import os
import threading
import tkinter as tk
from typing import Any, Callable, Dict, Optional
import customtkinter as ctk

from core.diagnostics import run_full_diagnostics, format_diagnostic_report_text


class DiagnosticWindow(ctk.CTkToplevel):
    """Finestra modale interattiva per il pre-flight check hardware."""

    def __init__(self, parent: tk.Tk, on_close: Optional[Callable[[], None]] = None):
        super().__init__(parent)
        self.on_close = on_close

        self.title("🩺 Diagnostica Hardware & Pre-Collaudo — SteadyMotion AI")
        self.geometry("720x680")
        self.minsize(640, 580)
        self.configure(fg_color="#0B0F19")
        self.lift()
        self.focus_force()

        self.diag_data: Optional[Dict[str, Any]] = None
        self.is_scanning = False

        self._build_ui()
        self._start_scan_thread()

    def _build_ui(self):
        # 1. Header
        header = ctk.CTkFrame(self, fg_color="#162032", corner_radius=12, border_width=1, border_color="#1E293B")
        header.pack(fill="x", padx=14, pady=(12, 6))

        title_lbl = ctk.CTkLabel(
            header,
            text="🩺 DIAGNOSTICA HARDWARE & AMBIENTE PRE-COLLAUDO",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#38BDF8",
        )
        title_lbl.pack(anchor="w", padx=14, pady=(10, 2))

        sub_lbl = ctk.CTkLabel(
            header,
            text="Verifica automatica di webcam USB, framerate reale erogato a 60 FPS, illuminazione e microfoni.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#94A3B8",
        )
        sub_lbl.pack(anchor="w", padx=14, pady=(0, 10))

        # 2. Card Risultato / Score Clinico
        self.score_card = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=12, border_width=1, border_color="#334155")
        self.score_card.pack(fill="x", padx=14, pady=6)

        self.lbl_verdict_badge = ctk.CTkLabel(
            self.score_card,
            text="ANALISI IN CORSO...",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#F59E0B",
        )
        self.lbl_verdict_badge.pack(pady=(12, 2))

        self.lbl_score_num = ctk.CTkLabel(
            self.score_card,
            text="Campionamento sensori in corso...",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#CBD5E1",
        )
        self.lbl_score_num.pack(pady=(0, 12))

        # 3. Dettagli Video e Audio (2 Colonne affiancate)
        details_frame = ctk.CTkFrame(self, fg_color="transparent")
        details_frame.pack(fill="both", expand=True, padx=14, pady=4)
        details_frame.grid_columnconfigure((0, 1), weight=1)

        # Colonna Sinistra: Webcam
        self.card_cam = ctk.CTkFrame(details_frame, fg_color="#162032", corner_radius=10, border_width=1, border_color="#1E293B")
        self.card_cam.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        ctk.CTkLabel(self.card_cam, text="📹 Sensore Video (Webcam)", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=12, pady=(10, 4))
        self.lbl_cam_details = ctk.CTkLabel(
            self.card_cam,
            text="Rilevamento in corso...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#E2E8F0",
            justify="left",
            wraplength=310,
        )
        self.lbl_cam_details.pack(anchor="w", padx=12, pady=(0, 10))

        # Colonna Destra: Audio
        self.card_audio = ctk.CTkFrame(details_frame, fg_color="#162032", corner_radius=10, border_width=1, border_color="#1E293B")
        self.card_audio.grid(row=0, column=1, padx=(6, 0), sticky="nsew")

        ctk.CTkLabel(self.card_audio, text="🎤 Dispositivi Audio (Microfono)", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=12, pady=(10, 4))
        self.lbl_audio_details = ctk.CTkLabel(
            self.card_audio,
            text="Rilevamento in corso...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#E2E8F0",
            justify="left",
            wraplength=310,
        )
        self.lbl_audio_details.pack(anchor="w", padx=12, pady=(0, 10))

        # 4. Box Consigli Caregiver
        self.adv_card = ctk.CTkFrame(self, fg_color="#162032", corner_radius=10, border_width=1, border_color="#1E293B")
        self.adv_card.pack(fill="x", padx=14, pady=6)

        ctk.CTkLabel(self.adv_card, text="💡 Indicazioni Pratiche per il Caregiver:", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#F59E0B").pack(anchor="w", padx=12, pady=(8, 2))
        self.lbl_recommendations = ctk.CTkLabel(
            self.adv_card,
            text="In attesa dei risultati della scansione...",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#CBD5E1",
            justify="left",
            wraplength=660,
        )
        self.lbl_recommendations.pack(anchor="w", padx=12, pady=(0, 8))

        # 5. Barra Inferiore Pulsanti
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=14, pady=(6, 12))

        self.btn_rescan = ctk.CTkButton(
            btn_bar,
            text="🔄 Ripeti Scansione",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#0284C7",
            hover_color="#0369A1",
            height=36,
            command=self._start_scan_thread,
        )
        self.btn_rescan.pack(side="left", padx=(0, 6))

        self.btn_save_report = ctk.CTkButton(
            btn_bar,
            text="💾 Salva Report su File",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="#334155",
            hover_color="#475569",
            height=36,
            command=self._save_report_file,
        )
        self.btn_save_report.pack(side="left", padx=6)

        btn_close = ctk.CTkButton(
            btn_bar,
            text="Chiudi",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="#1E293B",
            hover_color="#334155",
            text_color="#94A3B8",
            height=36,
            width=90,
            command=self._on_close,
        )
        btn_close.pack(side="right")

    def _start_scan_thread(self):
        if self.is_scanning:
            return
        self.is_scanning = True
        self.btn_rescan.configure(state="disabled", text="⏳ Scansione in corso...")
        self.lbl_verdict_badge.configure(text="TEST IN CORSO (5 SECONDI)...", text_color="#38BDF8")
        self.lbl_score_num.configure(text="Campionamento webcam a 60 Hz e stima rumore...")

        def _worker():
            data = run_full_diagnostics()
            if self.winfo_exists():
                self.after(0, lambda: self._apply_results(data))

        threading.Thread(target=_worker, daemon=True, name="DiagWorker").start()

    def _apply_results(self, diag: Dict[str, Any]):
        self.is_scanning = False
        self.diag_data = diag
        self.btn_rescan.configure(state="normal", text="🔄 Ripeti Scansione")

        # Score & Verdetto
        score = diag["score"]
        verdict = diag["verdict"]
        badge_color = diag["badge_color"]

        self.lbl_verdict_badge.configure(text=verdict, text_color=badge_color)
        self.lbl_score_num.configure(text=f"Punteggio di Idoneità Clinica: {score} / 100  |  Tempo analisi: {diag['duration_ms']} ms")

        # Webcam details
        cam = diag["active_camera"]
        if cam["success"]:
            cam_text = (
                f"• Stato: Attiva (Indice {cam['index']})\n"
                f"• Risoluzione: {cam['width']}x{cam['height']} px\n"
                f"• Framerate Reale: {cam['actual_fps']} FPS\n"
                f"• Codec MJPG: {'Sbloccato a 60 Hz ✅' if cam['mjpg_unlocked'] else 'Standard (30 Hz) ⚠️'}\n"
                f"• Luminanza: {cam['luma_mean']} nit ({cam['luma_status']})"
            )
        else:
            cam_text = (
                "• Stato: NON RILEVATA ❌\n"
                "• Causa: Nessuna fotocamera USB collegata\n"
                "• Fallback: Modalità Demo / Simulazione attiva a 60 FPS stabili"
            )
        self.lbl_cam_details.configure(text=cam_text)

        # Audio details
        aud = diag["audio"]
        if aud["available"]:
            aud_text = (
                f"• Dispositivo: {aud['default_device_name']}\n"
                f"• Sample Rate: {aud['default_sample_rate']} Hz\n"
                f"• Rumore Fondo: {aud['noise_db']} dB\n"
                f"• Valutazione: {aud['status']}"
            )
        else:
            aud_text = (
                "• Stato: Nessun microfono attivo rilevato ⚠️\n"
                "• Nota: Il Dwell Clicker e il puntamento funzionano normalmente anche senza microfono."
            )
        self.lbl_audio_details.configure(text=aud_text)

        # Consigli Caregiver
        rec_lines = [f"• {r}" for r in diag["recommendations"]]
        self.lbl_recommendations.configure(text="\n".join(rec_lines))

    def _save_report_file(self):
        if not self.diag_data:
            return
        report_text = format_diagnostic_report_text(self.diag_data)
        report_path = "report_diagnostica_hardware.txt"
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_text)
            self.btn_save_report.configure(text="✅ Salvato in report_diagnostica_hardware.txt")
            self.after(3000, lambda: self.btn_save_report.configure(text="💾 Salva Report su File"))
        except Exception:
            pass

    def _on_close(self):
        if self.on_close:
            self.on_close()
        self.destroy()
