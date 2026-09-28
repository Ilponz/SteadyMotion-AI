"""
Entry point principale per SteadyMotion AI v3.0 (Pure Software Edition).
Orchestra i 6 micro-argomenti:
1. Video Ingestion asincrona Zero-Copy a 60 FPS (DirectShow + MJPG)
2. Biometria MediaPipe Tasks VIDEO mode con fusione 6-DoF ed EAR Clamping
3. DSP One-Euro Isotropo 2D con spline cubica anti-tremore
4. Iniezione Sub-Pixel continua a 16-bit Win32 SendInput
5. Dwell Clicker con algoritmo Leaky Bucket (tolleranza agli spasmi)
6. Loop ad altissima precisione con timer Windows impostato a 1.0 ms
"""

import ctypes
import os
import sys
import threading
import time
import tkinter as tk
from typing import Any, Optional

from core.acoustic_trigger import AcousticTrigger
from core.camera_worker import CameraWorker
from core.dsp_filter import PointFilter2D
from core.dwell_clicker import DwellClicker
from core.tracker_engine import FaceTrackerEngine
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
        # Sblocco timer kernel Windows a 1.0 ms
        enable_high_precision_timer()

        self.root = tk.Tk()

        # Inizializzazione Sottosistemi
        self.mouse = WindowsMouseController()
        self.hud = DwellHUD(size=80)
        self.hud.init_window(self.root)

        # Modello MediaPipe Tasks
        model_path = os.path.join(os.path.dirname(__file__), "models", "face_landmarker.task")
        self.tracker = FaceTrackerEngine(model_path=model_path)

        # Parametri operativi di default
        self.gain = 2.8
        self.deadzone = 2.0
        self.min_cutoff = 1.2
        self.beta = 0.008
        self.is_paused = False

        # Filtro DSP Isotropo 2D
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
        self.acoustic.start()

        # Camera Worker (DirectShow, Buffer=1, FourCC MJPG, 60 FPS, Zero-Copy)
        self.camera = CameraWorker(camera_index=0, target_width=640, target_height=480, target_fps=60, use_mjpg=True)
        self.camera_ready = self.camera.start()

        # Pannello di Controllo GUI
        self.panel = ControlPanel(
            self.root,
            on_param_change=self._on_param_change,
            on_recenter=self.recenter,
            on_toggle_pause=self.toggle_pause,
        )

        # Chiusura pulita
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Thread di elaborazione real-time indipendente dalla GUI
        self.is_running = True
        self.tracking_thread: Optional[threading.Thread] = None

        # Telemetria e stato HUD thread-safe
        self.telemetry_lock = threading.Lock()
        self.shared_fps: float = 0.0
        self.shared_face_detected: bool = False
        self.shared_is_blinking: bool = False
        self.shared_hud_progress: float = 0.0
        self.shared_hud_x: int = 0
        self.shared_hud_y: int = 0
        self.shared_hud_dirty: bool = False

        # Stato tasti globali
        self.prev_f12 = False
        self.prev_f9 = False

    def _on_param_change(self, param_name: str, value: Any):
        if param_name == "gain":
            self.gain = float(value)
        elif param_name == "deadzone":
            self.deadzone = float(value) * 1000.0 if float(value) < 1.0 else float(value)
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
        """Calibra la postura neutrale del paziente come centro esatto dello schermo."""
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
            self.panel.pause_btn.config(text="▶ Riprendi (F9)")
            self.hud.hide()
        else:
            self.panel.pause_btn.config(text="⏸ Pausa (F9)")

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
        """Loop di elaborazione dedicato ad alta frequenza (60-120 FPS), disaccoppiato da Tkinter."""
        last_loop_time = time.perf_counter()
        loop_fps = 0.0

        while self.is_running:
            t_start = time.perf_counter()
            dt = t_start - last_loop_time
            if dt > 0:
                loop_fps = 0.9 * loop_fps + 0.1 * (1.0 / dt)
            last_loop_time = t_start

            # Controllo tasti scorciatoia ovunque su Windows (F12, F9)
            self._check_global_hotkeys()

            face_detected = False
            is_blinking = False

            if not self.is_paused:
                ret, frame, timestamp, _ = self.camera.get_latest_frame()
                if ret and frame is not None:
                    # Inferenza in modalità VIDEO con timestamp monotonico
                    res = self.tracker.process_frame(frame, timestamp_sec=t_start)
                    face_detected = res.face_detected
                    is_blinking = res.is_blinking

                    if face_detected and not is_blinking:
                        # Mappatura continua dello scostamento 6-DoF
                        norm_x = 0.5 + (res.cursor_raw_x - 0.5) * self.gain
                        norm_y = 0.5 + (res.cursor_raw_y - 0.5) * self.gain

                        # Limiti desktop virtuale
                        norm_x = max(0.0, min(1.0, norm_x))
                        norm_y = max(0.0, min(1.0, norm_y))

                        # Calcolo coordinate pixel in virgola mobile (sub-pixel)
                        target_px = self.mouse.vx + norm_x * self.mouse.vw
                        target_py = self.mouse.vy + norm_y * self.mouse.vh

                        # Filtraggio DSP One-Euro Isotropo 2D + Spline Deadzone
                        filt_x, filt_y = self.dsp_filter.filter(target_px, target_py, t_start)

                        # Iniezione nativa a 16-bit Win32 (sub-pixel continuo)
                        self.mouse.move_to_pixel(filt_x, filt_y)

                        # Aggiornamento Dwell Clicker (tolleranza elastica)
                        self.dwell_clicker.update(filt_x, filt_y, t_start)

            # Aggiornamento telemetria thread-safe
            with self.telemetry_lock:
                self.shared_fps = self.camera.actual_fps if self.camera.actual_fps > 0 else loop_fps
                self.shared_face_detected = face_detected
                self.shared_is_blinking = is_blinking

            # Sleep calibrato a bassa latenza per cadenza a 60-120 FPS
            elapsed = time.perf_counter() - t_start
            sleep_time = max(0.002, 0.016 - elapsed)
            time.sleep(sleep_time)

    def _gui_update_loop(self):
        """Aggiornamento fluido della GUI Tkinter e dell'HUD (30 FPS) senza rallentare il tracking."""
        if not self.is_running:
            return

        with self.telemetry_lock:
            fps = self.shared_fps
            face_detected = self.shared_face_detected
            is_blinking = self.shared_is_blinking
            hud_dirty = self.shared_hud_dirty
            progress = self.shared_hud_progress
            hx = self.shared_hud_x
            hy = self.shared_hud_y
            self.shared_hud_dirty = False

        if self.is_paused or not self.dwell_clicker.is_enabled:
            self.hud.hide()
        elif hud_dirty:
            self.hud.show_progress(progress, hx, hy)

        # Aggiornamento telemetria su GUI
        self.panel.update_telemetry(
            fps=fps,
            face_detected=face_detected,
            is_blinking=is_blinking,
            is_paused=self.is_paused,
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
        # Avvio del thread di elaborazione e controllo core
        self.tracking_thread = threading.Thread(
            target=self._core_tracking_loop,
            daemon=True,
            name="CoreTrackingWorker"
        )
        self.tracking_thread.start()

        # Avvio del loop GUI asincrono a 30 FPS
        self.root.after(50, self._gui_update_loop)
        self.root.mainloop()


if __name__ == "__main__":
    app = SteadyMotionApp()
    app.start()
