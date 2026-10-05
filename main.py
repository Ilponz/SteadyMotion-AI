"""
Entry point principale per SteadyMotion AI v3.0 (Pure Software Edition).
Orchestra i 6 micro-argomenti:
1. Video Ingestion asincrona Zero-Copy con Triple Buffering circolare e sincronizzazione event-driven
2. Biometria MediaPipe Tasks VIDEO mode con fusione 6-DoF, Bounding IPD ed EAR Clamping
3. DSP One-Euro Isotropo 2D rigoroso con Trailing Deadzone Continua
4. Iniezione Sub-Pixel continua a 16-bit Win32 SendInput (Zero Heap Churn e DPI Awareness v2)
5. Dwell Clicker con algoritmo Leaky Bucket e Gravity Well (tolleranza agli spasmi)
6. Interfaccia Human-Grade CustomTkinter v6 con temi Giorno/Notte, Radar Posturale e Modalità Demo
"""

import ctypes
import math
import os
import sys
import threading
import time
from typing import Any, Dict, Optional, Tuple
import customtkinter as ctk

from core.acoustic_trigger import AcousticTrigger
from core.camera_worker import CameraWorker
from core.dsp_filter import PointFilter2D
from core.dwell_clicker import DwellClicker
from core.tracker_engine import FaceTrackerEngine
from core.utils import get_resource_path
from core.virtual_input import (
    WindowsMouseController,
    enable_high_precision_timer,
    disable_high_precision_timer,
)
from gui.control_panel import ControlPanel
from gui.hud_overlay import DwellHUD

# Costanti Virtual Key Windows per Hotkey Globali
VK_F12 = 0x7B
VK_F9 = 0x78


class SteadyMotionApp:
    def __init__(self):
        # Sblocco timer kernel Windows a 1.0 ms e DPI awareness v2
        enable_high_precision_timer()

        self.root = ctk.CTk()

        # Inizializzazione Sottosistemi Win32 e Grafica
        self.mouse = WindowsMouseController()
        self.hud = DwellHUD(size=80)
        self.hud.init_window(self.root)

        # Modello MediaPipe Tasks (Risoluzione universale Dev & PyInstaller)
        model_path = get_resource_path(os.path.join("models", "face_landmarker.task"))
        self.tracker = FaceTrackerEngine(model_path=model_path)

        # Parametri operativi di default (Avvio sicuro in Standby - Cursore non dirottato)
        self.gain = 2.8
        self.gain_x_left = 2.8
        self.gain_x_right = 2.8
        self.gain_y_up = 2.8
        self.gain_y_down = 2.8
        self.is_custom_rom = False
        self.deadzone = 2.0
        self.min_cutoff = 1.1
        self.beta = 0.006
        self.is_paused = True

        # Filtro DSP One-Euro Isotropo 2D
        self.dsp_filter = PointFilter2D(
            min_cutoff=self.min_cutoff,
            beta=self.beta,
            deadzone_radius=self.deadzone,
        )

        # Dwell Clicker con tolleranza Leaky Bucket
        self.dwell_clicker = DwellClicker(
            dwell_time=0.65,
            tolerance_radius=24.0,
            click_callback=self._on_dwell_click,
            progress_callback=self._on_dwell_progress,
        )

        # Trigger Acustico Ausiliario (Microfono Webcam)
        self.acoustic = AcousticTrigger(
            threshold=0.18,
            debounce_time=0.40,
            callback=self._on_acoustic_click,
        )
        self.acoustic.is_enabled = False  # Spento di default, attivabile da preset o GUI
        self.acoustic.start()

        # Camera Worker (Triple Buffering, Buffer=1, FourCC MJPG, 60 FPS, Event-Driven)
        self.camera = CameraWorker(
            camera_index=0,
            target_width=640,
            target_height=480,
            target_fps=60,
            use_mjpg=True,
            mirror_image=True,
        )
        self.camera_ready = self.camera.start()
        # Fallback automatico su modalità Demo se non c'è webcam fisica collegata
        self.is_demo = not self.camera_ready

        # Pannello di Controllo GUI Moderno (CustomTkinter)
        self.panel = ControlPanel(
            self.root,
            on_param_change=self._on_param_change,
            on_recenter=self.recenter,
            on_toggle_pause=self.toggle_pause,
            on_calibrate_audio=self.calibrate_audio,
            on_toggle_demo=self.toggle_demo,
            on_open_calibration=self.open_calibration_window,
            on_reset_rom=self.reset_symmetric_gain,
            on_open_keyboard=self.open_floating_keyboard,
            on_open_diagnostics=self.open_diagnostic_window,
        )
        self.panel.demo_mode.set(self.is_demo)

        # Chiusura pulita
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Thread di elaborazione real-time indipendente dalla GUI
        self.is_running = True
        self.tracking_thread: Optional[threading.Thread] = None

        # Telemetria e stato HUD thread-safe
        self.telemetry_lock = threading.Lock()
        self.shared_fps: float = 0.0
        self.shared_luma: float = 120.0
        self.shared_mic_vol: float = 0.0
        self.shared_yaw: float = 0.0
        self.shared_pitch: float = 0.0
        self.shared_roll: float = 0.0
        self.shared_raw_x: float = 0.5
        self.shared_raw_y: float = 0.5
        self.shared_face_detected: bool = False
        self.shared_is_blinking: bool = False
        self.shared_hud_progress: float = 0.0
        self.shared_hud_x: int = 0
        self.shared_hud_y: int = 0
        self.shared_hud_dirty: bool = False

        # Stato tasti globali
        self.prev_f12 = False
        self.prev_f9 = False

    def toggle_demo(self, enabled: bool):
        """Attiva o disattiva la modalità demo di simulazione cefalica."""
        self.is_demo = enabled

    def apply_asymmetric_gains(self, gains: Dict[str, float]):
        """Applica i guadagni asimmetrici derivati dalla calibrazione ROM a 5 punti."""
        self.gain_x_left = float(gains.get("gain_x_left", self.gain))
        self.gain_x_right = float(gains.get("gain_x_right", self.gain))
        self.gain_y_up = float(gains.get("gain_y_up", self.gain))
        self.gain_y_down = float(gains.get("gain_y_down", self.gain))
        self.is_custom_rom = True
        self.panel.update_rom_gains(gains, is_custom=True)

    def reset_symmetric_gain(self):
        """Ripristina il guadagno uniforme simmetrico."""
        self.is_custom_rom = False
        self.gain_x_left = self.gain
        self.gain_x_right = self.gain
        self.gain_y_up = self.gain
        self.gain_y_down = self.gain
        self.panel.update_rom_gains({
            "gain_x_left": self.gain,
            "gain_x_right": self.gain,
            "gain_y_up": self.gain,
            "gain_y_down": self.gain,
        }, is_custom=False)

    def get_current_pose(self) -> Dict[str, Any]:
        """Restituisce la posa e telemetria corrente per la finestra di calibrazione."""
        with self.telemetry_lock:
            return {
                "face_detected": self.shared_face_detected,
                "raw_x": self.shared_raw_x,
                "raw_y": self.shared_raw_y,
                "yaw": self.shared_yaw,
                "pitch": self.shared_pitch,
                "roll": self.shared_roll,
            }

    def open_calibration_window(self):
        """Apre la finestra modale a schermo intero per la calibrazione a 5 punti."""
        from gui.calibration_window import CalibrationWindow
        CalibrationWindow(
            parent=self.root,
            pose_provider=self.get_current_pose,
            on_calibration_complete=lambda gains, stats: self.apply_asymmetric_gains(gains),
        )

    def open_floating_keyboard(self):
        """Apre o porta in primo piano la tastiera assistiva flottante."""
        if hasattr(self, "_floating_kbd") and self._floating_kbd is not None and self._floating_kbd.winfo_exists():
            self._floating_kbd.lift()
            self._floating_kbd.focus_force()
            return
        from gui.floating_keyboard import FloatingKeyboardWindow
        self._floating_kbd = FloatingKeyboardWindow(
            parent=self.root,
            virtual_input_controller=self.mouse,
            on_close_callback=lambda: setattr(self, "_floating_kbd", None),
        )

    def open_diagnostic_window(self):
        """Apre la finestra di diagnostica hardware per webcam e microfono."""
        if hasattr(self, "_diag_window") and self._diag_window is not None and self._diag_window.winfo_exists():
            self._diag_window.lift()
            self._diag_window.focus_force()
            return
        from gui.diagnostic_window import DiagnosticWindow
        self._diag_window = DiagnosticWindow(
            parent=self.root,
            on_close=lambda: setattr(self, "_diag_window", None),
        )

    def _on_param_change(self, param_name: str, value: Any):
        if param_name == "gain":
            self.gain = float(value)
            if not self.is_custom_rom:
                self.gain_x_left = self.gain
                self.gain_x_right = self.gain
                self.gain_y_up = self.gain
                self.gain_y_down = self.gain
        elif param_name == "deadzone":
            self.deadzone = float(value)
            self.dsp_filter.update_params(self.min_cutoff, self.beta, self.deadzone)
        elif param_name == "min_cutoff":
            self.min_cutoff = float(value)
            self.dsp_filter.update_params(self.min_cutoff, self.beta, self.deadzone)
        elif param_name == "beta":
            self.beta = float(value)
            self.dsp_filter.update_params(self.min_cutoff, self.beta, self.deadzone)
        elif param_name == "dwell_enabled":
            self.dwell_clicker.is_enabled = bool(value)
            if not self.dwell_clicker.is_enabled:
                self.hud.hide()
        elif param_name == "dwell_time":
            self.dwell_clicker.dwell_time = float(value)
        elif param_name == "acoustic_enabled":
            self.acoustic.update_params(enabled=bool(value), threshold=self.acoustic.threshold)
        elif param_name == "acoustic_threshold":
            self.acoustic.update_params(enabled=self.acoustic.is_enabled, threshold=float(value))

    def _on_dwell_click(self, action: str, x: int, y: int):
        if self.is_paused:
            return
        if action == "left":
            self.mouse.click("left")
        elif action == "right":
            self.mouse.click("right")
        elif action == "double":
            self.mouse.double_click()
        elif action == "drag":
            self.mouse.toggle_drag()

    def _on_dwell_progress(self, progress: float, x: int, y: int):
        if self.is_paused:
            return
        with self.telemetry_lock:
            self.shared_hud_progress = progress
            self.shared_hud_x = x
            self.shared_hud_y = y
            self.shared_hud_dirty = True

    def _on_acoustic_click(self):
        """Genera un clic immediato all'impulso acustico."""
        if not self.is_paused:
            self.mouse.click("left")

    def recenter(self):
        """Calibra la postura neutrale comoda del paziente come centro esatto del desktop."""
        if self.is_demo:
            self.dsp_filter.reset()
            self.dwell_clicker.cancel()
            return

        ret, frame, ts, _ = self.camera.get_latest_frame()
        if ret and frame is not None:
            res = self.tracker.process_frame(frame, timestamp_sec=ts)
            if res.face_detected:
                self.tracker.calibrate_center(
                    res.yaw + self.tracker.neutral_yaw,
                    res.pitch + self.tracker.neutral_pitch,
                    res.cursor_raw_x,
                    res.cursor_raw_y,
                    self.tracker.neutral_ipd,
                )
        self.dsp_filter.reset()
        self.dwell_clicker.cancel()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.hud.hide()

    def _check_global_hotkeys(self):
        """Intercetta F12 ed F9 a livello OS globale."""
        f12_pressed = bool(ctypes.windll.user32.GetAsyncKeyState(VK_F12) & 0x8000)
        if f12_pressed and not self.prev_f12:
            self.recenter()
        self.prev_f12 = f12_pressed

        f9_pressed = bool(ctypes.windll.user32.GetAsyncKeyState(VK_F9) & 0x8000)
        if f9_pressed and not self.prev_f9:
            self.toggle_pause()
        self.prev_f9 = f9_pressed

    def _core_tracking_loop(self):
        """
        Loop di elaborazione dedicato ad alta frequenza (60-120 FPS).
        Sincronizzato sull'arrivo dei frame hardware della webcam o generatore demo sintetico.
        """
        last_loop_time = time.perf_counter()
        loop_fps = 0.0

        while self.is_running:
            self._check_global_hotkeys()
            t_now = time.perf_counter()

            face_detected = False
            is_blinking = False
            yaw, pitch, roll = 0.0, 0.0, 0.0

            # ---------------- MODALITÀ DEMO SINTETICA (SENZA FOTOCAMERA) ----------------
            if self.is_demo:
                loop_fps = 60.0
                face_detected = True
                is_blinking = False

                sim_t = t_now * 0.7
                # Simulazione traiettoria cefalica + micro-tremore a 5 Hz
                raw_x = 0.5 + 0.14 * math.sin(sim_t) + 0.002 * math.sin(t_now * 31.4)
                raw_y = 0.5 + 0.10 * math.cos(sim_t * 0.8) + 0.002 * math.cos(t_now * 31.4)
                yaw = 7.0 * math.sin(sim_t)
                pitch = 4.0 * math.cos(sim_t * 0.8)
                roll = 2.0 * math.sin(sim_t * 0.5)

                if not self.is_paused:
                    dx = raw_x - 0.5
                    dy = raw_y - 0.5
                    gx = self.gain_x_left if dx < 0.0 else self.gain_x_right
                    gy = self.gain_y_up if dy < 0.0 else self.gain_y_down

                    norm_x = max(0.0, min(1.0, 0.5 + dx * gx))
                    norm_y = max(0.0, min(1.0, 0.5 + dy * gy))

                    target_px = self.mouse.vx + norm_x * self.mouse.vw
                    target_py = self.mouse.vy + norm_y * self.mouse.vh

                    filt_x, filt_y = self.dsp_filter.filter(target_px, target_py, t_now)
                    self.mouse.move_to_pixel(filt_x, filt_y)
                    self.dwell_clicker.update(filt_x, filt_y, t_now)

                with self.telemetry_lock:
                    self.shared_fps = loop_fps
                    self.shared_face_detected = face_detected
                    self.shared_is_blinking = is_blinking
                    self.shared_yaw = yaw
                    self.shared_pitch = pitch
                    self.shared_roll = roll
                    self.shared_raw_x = raw_x
                    self.shared_raw_y = raw_y

                time.sleep(0.016)
                continue

            # ---------------- MODALITÀ HARDWARE WEBCAM REALE ----------------
            ret, frame, timestamp, _ = self.camera.wait_for_frame(timeout=0.035)

            dt = t_now - last_loop_time
            if dt > 0:
                loop_fps = 0.9 * loop_fps + 0.1 * (1.0 / dt)
            last_loop_time = t_now

            raw_x, raw_y = 0.5, 0.5
            if ret and frame is not None:
                res = self.tracker.process_frame(frame, timestamp_sec=t_now)
                face_detected = res.face_detected
                is_blinking = res.is_blinking
                yaw = res.yaw
                pitch = res.pitch
                roll = res.roll
                raw_x = res.cursor_raw_x
                raw_y = res.cursor_raw_y

                # Iniezione mouse e Clic a sosta eseguiti SOLO se armato (non in pausa)
                if face_detected and not is_blinking and not self.is_paused:
                    dx = raw_x - 0.5
                    dy = raw_y - 0.5
                    gx = self.gain_x_left if dx < 0.0 else self.gain_x_right
                    gy = self.gain_y_up if dy < 0.0 else self.gain_y_down

                    norm_x = max(0.0, min(1.0, 0.5 + dx * gx))
                    norm_y = max(0.0, min(1.0, 0.5 + dy * gy))

                    target_px = self.mouse.vx + norm_x * self.mouse.vw
                    target_py = self.mouse.vy + norm_y * self.mouse.vh

                    filt_x, filt_y = self.dsp_filter.filter(target_px, target_py, t_now)
                    self.mouse.move_to_pixel(filt_x, filt_y)
                    self.dwell_clicker.update(filt_x, filt_y, t_now)

            with self.telemetry_lock:
                self.shared_fps = self.camera.actual_fps if self.camera.actual_fps > 0 else loop_fps
                self.shared_luma = self.camera.current_luma
                self.shared_mic_vol = self.acoustic.current_volume
                self.shared_face_detected = face_detected
                self.shared_is_blinking = is_blinking
                self.shared_yaw = yaw
                self.shared_pitch = pitch
                self.shared_roll = roll
                if face_detected:
                    self.shared_raw_x = raw_x
                    self.shared_raw_y = raw_y

    def calibrate_audio(self):
        """Avvia la routine di stima del rumore ambientale per 2 secondi."""
        self.acoustic.start_auto_calibration(
            duration=2.0,
            on_complete=lambda th: self.root.after(0, lambda: self.panel.update_calibrated_threshold(th)),
        )

    def _gui_update_loop(self):
        """Aggiornamento fluido della GUI Tkinter e dell'HUD (30 FPS) senza rallentare il tracking."""
        if not self.is_running:
            return

        with self.telemetry_lock:
            fps = self.shared_fps
            luma = self.shared_luma
            mic_vol = self.shared_mic_vol
            face_detected = self.shared_face_detected
            is_blinking = self.shared_is_blinking
            yaw = self.shared_yaw
            pitch = self.shared_pitch
            roll = self.shared_roll
            hud_dirty = self.shared_hud_dirty
            progress = self.shared_hud_progress
            hx = self.shared_hud_x
            hy = self.shared_hud_y
            self.shared_hud_dirty = False

        if self.is_paused or not self.dwell_clicker.is_enabled:
            self.hud.hide()
        elif hud_dirty:
            self.hud.show_progress(progress, hx, hy)

        # Aggiornamento telemetria, radar e VU meter su CustomTkinter
        self.panel.update_telemetry(
            fps=fps,
            face_detected=face_detected,
            is_blinking=is_blinking,
            is_paused=self.is_paused,
            luma=luma,
            mic_volume=mic_vol,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
        )

        self.root.after(33, self._gui_update_loop)

    def on_close(self):
        """Spegnimento pulito e rilascio delle risorse."""
        self.is_running = False
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=1.0)
        disable_high_precision_timer()
        self.camera.stop()
        self.acoustic.stop()
        self.hud.hide()
        self.root.destroy()
        sys.exit(0)

    def start(self):
        self.tracking_thread = threading.Thread(
            target=self._core_tracking_loop,
            daemon=True,
            name="CoreTrackingWorker",
        )
        self.tracking_thread.start()

        self.root.after(50, self._gui_update_loop)
        self.root.mainloop()


if __name__ == "__main__":
    app = SteadyMotionApp()
    app.start()
