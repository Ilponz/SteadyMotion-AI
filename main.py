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
from core.ballistics import BallisticTransfer
from core.camera_worker import CameraWorker
from core.clinical_logger import ClinicalSessionLogger
from core.license_manager import LicenseManager
from core.copilot import CaregiverCoPilot
from core.dsp_filter import PointFilter2D
from core.dwell_clicker import DwellClicker
from core.dwell_safety import DwellSafetyGuard
from core.gaze_sleep import GazeSleepController
from core.edge_scrolling import EdgeScrollController
from core.ergonomics import ErgonomicsMonitor
from core.audio_feedback import AudioFeedback
from core.gesture_trigger import GestureTrigger
from core.magnetic_snapping import MagneticSnapper
from core.wheelchair_jolt import WheelchairJoltFilter
from core.ataxia_filter import AtaxiaIntentionDamper
from core.spasm_clamp import SpasmVelocityClamp
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
VK_PAUSE = 0x13
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_S = 0x53


class SteadyMotionApp:
    def __init__(self, force_demo: bool = False):
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

        # Feedback Uditivo Asincrono dei Clic (Multi-Sensoriale)
        self.audio_feedback = AudioFeedback(enabled=True)

        # Dwell Clicker con tolleranza Leaky Bucket, Anti-Sweep Gate, Freno Spasmo e Micro-Tick di Cadenza
        self.dwell_clicker = DwellClicker(
            dwell_time=0.65,
            tolerance_radius=24.0,
            click_callback=self._on_dwell_click,
            progress_callback=self._on_dwell_progress,
            spasm_callback=self._on_spasm_shock,
            cadence_callback=lambda level: self.audio_feedback.play("dwell_tick"),
        )
        self._base_dwell_time: float = self.dwell_clicker.dwell_time
        self.dwell_safety = DwellSafetyGuard(
            is_enabled=True,
            safety_multiplier=1.75,
            vx=self.mouse.vx,
            vy=self.mouse.vy,
            vw=self.mouse.vw,
            vh=self.mouse.vh,
        )

        # Trigger Acustico Ausiliario (Microfono Webcam)
        self.acoustic = AcousticTrigger(
            threshold=0.18,
            debounce_time=0.40,
            callback=self._on_acoustic_click,
        )
        self.acoustic.is_enabled = False  # Spento di default, attivabile da preset o GUI
        self.acoustic.start()

        # Filtro Anti-Sobbalzo Meccanico per Carrozzine Elettroniche (Wheelchair Seismic Jolt Absorber)
        self.wheelchair_jolt = WheelchairJoltFilter(is_enabled=True)

        # Smorzatore Dinamico per Atassia Cerebellare (Tremore Intenzionale Terminale 2.5 - 4.5 Hz)
        self.ataxia_damper = AtaxiaIntentionDamper(is_enabled=True)

        # Freno Biometrico Anti-Teletrasporto per Spasmi Distonici e Scatti Acuti
        self.spasm_clamp = SpasmVelocityClamp(is_enabled=True)

        # Monitor Ergonomico & Rilevamento Affaticamento Muscolare Cervicale
        self.ergonomics_monitor = ErgonomicsMonitor()

        # Funzione di Trasferimento Balistica Non-Lineare (Fitts's Law gamma=1.25)
        self.ballistics = BallisticTransfer(gamma=1.25, is_enabled=True, sniper_mode=True)

        # Caregiver Co-Pilot (Arbitraggio Mouse Fisico USB)
        self.copilot = CaregiverCoPilot(
            threshold_px=24.0,
            pause_duration=2.0,
            on_override_start=self._on_copilot_start,
            on_override_end=self._on_copilot_end,
        )

        # UI Automation & Accessibility Magnetic Target Snapping
        self.magnetic_snapper = MagneticSnapper(
            snap_radius=36.0,
            gravity_factor=0.65,
            escape_velocity=280.0,
            is_enabled=True,
        )

        # Controllore di Scorrimento Continuo ai Bordi dello Schermo (Edge Scrolling)
        self.edge_scrolling = EdgeScrollController(
            scroll_callback=lambda clicks: self.mouse.scroll(clicks),
            margin_px=24,
            dwell_activation_delay=0.35,
            scroll_interval=0.14,
            is_enabled=True,
        )

        # Centratura Automatica Intelligente (Auto-Recenter dopo Assenza Volto)
        self.auto_recenter_enabled = True
        self.was_face_lost = False
        self.face_lost_timestamp = 0.0
        self.face_stable_since = 0.0
        self.stable_reference_pose = None

        # Trigger Gesti Facciali Silenziosi (FACS Blendshapes: Jaw Open, Smile, Brow)
        self.gesture_trigger = GestureTrigger(
            gesture_type="jaw_open",
            trigger_threshold=0.45,
            release_threshold=0.20,
            debounce_sec=0.45,
            click_callback=self._on_gesture_click,
            is_enabled=False,
        )

        # Controllore di Sospensione e Risveglio a Sguardo Autonomo (Paziente SLA / Tetraplegia)
        self.gaze_sleep = GazeSleepController(
            wake_dwell_time=1.8,
            on_sleep_callback=self._on_gaze_sleep,
            on_wake_callback=self._on_gaze_wake,
        )
        wake_cx = int(self.mouse.vx + self.mouse.vw * 0.5)
        self.gaze_sleep.set_wake_target_rect(wake_cx - 60, int(self.mouse.vy + 10), wake_cx + 60, int(self.mouse.vy + 70))

        # Telemetria Clinica & Cartella Riabilitativa Digitale (ASL/SSN)
        self.clinical_logger = ClinicalSessionLogger()

        # Gestione Licenza Commerciale & Periodo di Prova
        self.license_manager = LicenseManager()

        # Camera Worker (Triple Buffering, Buffer=1, FourCC MJPG, 60 FPS, Event-Driven)
        self.camera = CameraWorker(
            camera_index=0,
            target_width=640,
            target_height=480,
            target_fps=60,
            use_mjpg=True,
            mirror_image=True,
        )
        if force_demo:
            self.camera_ready = False
            self.is_demo = True
        else:
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
            on_open_palette=self.open_action_palette,
            on_open_fitts=self.open_fitts_assessment_window,
            on_switch_camera=self.switch_camera_source,
            clinical_logger=self.clinical_logger,
            license_manager=self.license_manager,
        )
        self.panel.demo_mode.set(self.is_demo)
        self._action_palette = None

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
        self.shared_is_fatigued: bool = False
        self.shared_fatigue_reason: str = "Nessuna"
        self.shared_is_copilot: bool = False
        self.shared_is_snapped: bool = False

        # Stato tasti globali
        self.prev_f12 = False
        self.prev_f9 = False
        self.prev_panic = False

    def _on_copilot_start(self):
        """Notifica acustica e disarmo temporaneo per intervento fisico caregiver."""
        if self.mouse.is_dragging:
            self.mouse.mouse_up("left")
        self.audio_feedback.play("pause")
        self.hud.hide()

    def _on_copilot_end(self):
        """Ripristino del controllo cefalico dopo l'intervento del caregiver."""
        self.audio_feedback.play("resume")

    def _on_gesture_click(self, gesture: str):
        """Genera un clic istantaneo e silenzioso al riconoscimento del gesto facciale."""
        if not self.is_paused:
            self.mouse.click("left")
            self.audio_feedback.play("click_left")

    def _on_spasm_shock(self):
        """Registra un picco di spasmo motorio acuto nella cartella clinica."""
        self.clinical_logger.record_spasm_shock()

    def toggle_demo(self, enabled: bool):
        """Attiva o disattiva la modalità demo di simulazione cefalica."""
        self.is_demo = enabled

    def switch_camera_source(self, camera_index: int) -> bool:
        """Commuta la sorgente webcam a caldo."""
        ok = self.camera.switch_camera(camera_index)
        if ok:
            self.camera_ready = True
            self.is_demo = False
            self.panel.demo_mode.set(False)
        return ok

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
            on_calibration_complete=self._on_rom_calibration_complete,
        )

    def open_fitts_assessment_window(self):
        """Apre la finestra modale a schermo intero per la valutazione clinica ISO 9241-9."""
        from gui.fitts_window import FittsAssessmentWindow
        FittsAssessmentWindow(
            parent=self.root,
            on_assessment_complete=lambda summary: self.clinical_logger.record_fitts_assessment(summary),
            audio_feedback=self.audio_feedback,
        )

    def _on_rom_calibration_complete(self, gains, stats):
        self.apply_asymmetric_gains(gains)
        if isinstance(stats, dict) and "bcea" in stats:
            b = stats["bcea"]
            bcea_68 = float(b.get("bcea_68", 0.0))
            bcea_95 = float(b.get("bcea_95", 0.0))
            grade = str(b.get("stability_grade", "NON_VALUTATA"))
            self.clinical_logger.record_bcea_stability(
                bcea_68=bcea_68,
                bcea_95=bcea_95,
                stability_grade=grade,
            )
            # Applicazione automatica parametri Dwell ottimizzati in base alla stabilità
            if stats.get("apply_recommended_dwell"):
                new_dwell = float(stats.get("recommended_dwell", self.dwell_clicker.dwell_time))
                new_tol = float(stats.get("recommended_tolerance", self.dwell_clicker.tolerance_radius))
                self.dwell_clicker.dwell_time = new_dwell
                self._base_dwell_time = new_dwell
                self.dwell_clicker.tolerance_radius = new_tol
                self.clinical_logger.record_dwell_adaptation(
                    dwell_time=new_dwell,
                    tolerance_radius=new_tol,
                    source="BCEA_ROM_CALIBRATION",
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
            clinical_logger=self.clinical_logger,
            audio_feedback=self.audio_feedback,
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

    def open_action_palette(self):
        """Apre la mini-barra flottante delle azioni del mouse (Left, Right, Double, Drag, Scroll)."""
        if hasattr(self, "_action_palette") and self._action_palette is not None and self._action_palette.winfo_exists():
            self._action_palette.lift()
            self._action_palette.focus_force()
            return
        from gui.action_palette import FloatingActionPaletteWindow
        self._action_palette = FloatingActionPaletteWindow(
            parent=self.root,
            dwell_clicker=self.dwell_clicker,
            virtual_input=self.mouse,
            on_toggle_pause=self.toggle_pause,
            on_toggle_keyboard=self.open_floating_keyboard,
            on_close_callback=lambda: setattr(self, "_action_palette", None),
        )
        self._action_palette.set_pause_state(self.is_paused)

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
            self._base_dwell_time = float(value)
            self.dwell_clicker.dwell_time = float(value)
        elif param_name == "dwell_safety_enabled":
            self.dwell_safety.is_enabled = bool(value)
        elif param_name == "acoustic_enabled":
            self.acoustic.update_params(enabled=bool(value), threshold=self.acoustic.threshold)
        elif param_name == "acoustic_threshold":
            self.acoustic.update_params(enabled=self.acoustic.is_enabled, threshold=float(value))
        elif param_name == "audio_feedback_enabled":
            self.audio_feedback.set_enabled(bool(value))
        elif param_name == "soundpack":
            self.audio_feedback.set_soundpack(str(value))
        elif param_name == "gamma":
            self.ballistics.update_params(gamma=float(value), is_enabled=self.ballistics.is_enabled, sniper_mode=self.ballistics.sniper_mode)
        elif param_name == "ballistics_enabled":
            self.ballistics.update_params(gamma=self.ballistics.gamma, is_enabled=bool(value), sniper_mode=self.ballistics.sniper_mode)
        elif param_name == "ballistics_sniper":
            self.ballistics.update_params(gamma=self.ballistics.gamma, is_enabled=self.ballistics.is_enabled, sniper_mode=bool(value))
        elif param_name == "copilot_enabled":
            self.copilot.is_enabled = bool(value)
        elif param_name == "hud_theme":
            self.hud.set_theme(str(value))
        elif param_name == "hud_size":
            self.hud.set_size(int(value))
        elif param_name == "magnetic_snapping_enabled":
            self.magnetic_snapper.update_params(is_enabled=bool(value))
        elif param_name == "magnetic_gravity":
            self.magnetic_snapper.update_params(gravity_factor=float(value))
        elif param_name == "magnetic_radius":
            self.magnetic_snapper.update_params(snap_radius=float(value))
        elif param_name == "edge_scrolling_enabled":
            self.edge_scrolling.set_enabled(bool(value))
        elif param_name == "auto_recenter_enabled":
            self.auto_recenter_enabled = bool(value)
        elif param_name == "gesture_enabled":
            self.gesture_trigger.update_params(is_enabled=bool(value))
        elif param_name == "gesture_type":
            self.gesture_trigger.update_params(gesture_type=str(value))
        elif param_name == "gesture_threshold":
            self.gesture_trigger.update_params(trigger_threshold=float(value))

    def _on_dwell_click(self, action: str, x: int, y: int):
        if self.is_paused:
            return
        self.clinical_logger.record_dwell_click(action)

        # Gestione automatica completamento Drag & Drop sul bersaglio di arrivo
        if self.mouse.is_dragging:
            self.mouse.mouse_up("left")
            self.audio_feedback.play("drag_end")
            if hasattr(self, "_action_palette") and self._action_palette is not None and self._action_palette.winfo_exists():
                self._action_palette.on_click_completed("drag")
            return

        if action == "left":
            self.mouse.click("left")
            self.audio_feedback.play("click_left")
        elif action == "right":
            self.mouse.click("right")
            self.audio_feedback.play("click_right")
        elif action == "double":
            self.mouse.double_click()
            self.audio_feedback.play("double_click")
        elif action == "drag":
            self.mouse.toggle_drag()
            if self.mouse.is_dragging:
                self.audio_feedback.play("drag_start")
            else:
                self.audio_feedback.play("drag_end")
        elif action == "scroll_up":
            self.mouse.scroll(3)
            self.audio_feedback.play("click_left")
        elif action == "scroll_down":
            self.mouse.scroll(-3)
            self.audio_feedback.play("click_left")

        if hasattr(self, "_action_palette") and self._action_palette is not None and self._action_palette.winfo_exists():
            self._action_palette.on_click_completed(action)

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
            self.clinical_logger.record_acoustic_click()
            self.mouse.click("left")
            self.audio_feedback.play("click_left")

    def _on_gaze_sleep(self):
        if self.mouse.is_dragging:
            self.mouse.mouse_up("left")
        self.dwell_clicker.cancel()
        self.hud.hide()

    def _on_gaze_wake(self):
        self.audio_feedback.play("resume")

    def recenter(self):
        """Calibra la postura neutrale comoda del paziente come centro esatto del desktop."""
        if self.is_demo:
            self.dsp_filter.reset()
            self.magnetic_snapper.reset()
            self.dwell_clicker.cancel()
            self.tracker.set_adaptive_bias(0.0, 0.0)
            self.ergonomics_monitor.reset_reference()
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
                self.tracker.set_adaptive_bias(0.0, 0.0)
                self.ergonomics_monitor.reset_reference(res.yaw, res.pitch, res.roll)
        self.dsp_filter.reset()
        self.ataxia_damper.reset()
        self.spasm_clamp.reset()
        self.magnetic_snapper.reset()
        self.dwell_clicker.cancel()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused and self.mouse.is_dragging:
            self.mouse.mouse_up("left")
        self.clinical_logger.set_tracking_state(not self.is_paused)
        if self.is_paused:
            self.hud.hide()
            self.audio_feedback.play("pause")
        else:
            self.audio_feedback.play("resume")
        if hasattr(self, "_action_palette") and self._action_palette is not None and self._action_palette.winfo_exists():
            self._action_palette.set_pause_state(self.is_paused)

    def _check_global_hotkeys(self):
        """Intercetta F12, F9 e il Panic Kill-Switch (Pause o Ctrl+Alt+S) a livello OS globale."""
        f12_pressed = bool(ctypes.windll.user32.GetAsyncKeyState(VK_F12) & 0x8000)
        if f12_pressed and not self.prev_f12:
            self.recenter()
        self.prev_f12 = f12_pressed

        f9_pressed = bool(ctypes.windll.user32.GetAsyncKeyState(VK_F9) & 0x8000)
        if f9_pressed and not self.prev_f9:
            self.toggle_pause()
        self.prev_f9 = f9_pressed

        # Panic Kill-Switch Caregiver (Tasto Pause/Break o combinazione Ctrl+Alt+S)
        pause_pressed = bool(ctypes.windll.user32.GetAsyncKeyState(VK_PAUSE) & 0x8000)
        ctrl_pressed = bool(ctypes.windll.user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
        alt_pressed = bool(ctypes.windll.user32.GetAsyncKeyState(VK_MENU) & 0x8000)
        s_pressed = bool(ctypes.windll.user32.GetAsyncKeyState(VK_S) & 0x8000)
        panic_pressed = pause_pressed or (ctrl_pressed and alt_pressed and s_pressed)

        if panic_pressed and not self.prev_panic:
            self.emergency_panic_disarm()
        self.prev_panic = panic_pressed

    def emergency_panic_disarm(self):
        """Disarmo immediato di emergenza per il caregiver (Panic Kill-Switch)."""
        if not self.is_paused:
            self.toggle_pause()
        elif self.mouse.is_dragging:
            self.mouse.mouse_up("left")

    def _core_tracking_loop(self):
        """
        Loop di elaborazione dedicato ad alta frequenza (60-120 FPS).
        Sincronizzato sull'arrivo dei frame hardware della webcam o generatore demo sintetico.
        """
        last_loop_time = time.perf_counter()
        loop_fps = 0.0
        last_metric_check = 0.0

        while self.is_running:
            self._check_global_hotkeys()
            t_now = time.perf_counter()

            # Controllo periodico cambio risoluzione o hotplug multi-monitor ogni 1.5s
            if t_now - last_metric_check > 1.5:
                if self.mouse.check_screen_metrics_changed():
                    self.dwell_safety.update_screen_geometry(self.mouse.vx, self.mouse.vy, self.mouse.vw, self.mouse.vh)
                    wake_cx = int(self.mouse.vx + self.mouse.vw * 0.5)
                    self.gaze_sleep.set_wake_target_rect(wake_cx - 60, int(self.mouse.vy + 10), wake_cx + 60, int(self.mouse.vy + 70))
                last_metric_check = t_now

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
                raw_y, is_jolt = self.wheelchair_jolt.filter_y(raw_y, t_now)
                if is_jolt:
                    if self.dwell_clicker.progress > 0.0:
                        self.dwell_clicker.cancel()
                        self.clinical_logger.record_dwell_aborted()
                    self.clinical_logger.record_wheelchair_jolt()
                yaw = 7.0 * math.sin(sim_t)
                pitch = 4.0 * math.cos(sim_t * 0.8)
                roll = 2.0 * math.sin(sim_t * 0.5)

                if not self.is_paused:
                    norm_x, norm_y = self.ballistics.compute_normalized_xy(
                        raw_x, raw_y, self.gain_x_left, self.gain_x_right, self.gain_y_up, self.gain_y_down, now=t_now
                    )

                    target_px = self.mouse.vx + norm_x * self.mouse.vw
                    target_py = self.mouse.vy + norm_y * self.mouse.vh

                    filt_x, filt_y = self.dsp_filter.filter(target_px, target_py, t_now)
                    atax_x, atax_y, _ = self.ataxia_damper.process(filt_x, filt_y, t_now)
                    clamped_x, clamped_y, is_spasm = self.spasm_clamp.clamp(atax_x, atax_y, t_now)
                    if is_spasm:
                        if self.dwell_clicker.progress > 0.0:
                            self.dwell_clicker.cancel()
                            self.clinical_logger.record_dwell_aborted()
                        self.clinical_logger.record_spasm_shock()
                        self.clinical_logger.record_dystonic_teleport_clamped()
                    snap_x, snap_y = self.magnetic_snapper.apply_snap(clamped_x, clamped_y, t_now)

                    act_x, act_y = self.mouse.get_cursor_pos()
                    is_overridden = self.copilot.check_override(act_x, act_y, t_now)
                    if not is_overridden:
                        self.mouse.move_to_pixel(snap_x, snap_y)
                        self.copilot.record_injection(snap_x, snap_y)
                        self.clinical_logger.record_cursor_movement(snap_x, snap_y)

                        # Verifica Edge Scrolling continuo ai bordi dello schermo
                        cur_mon = self.mouse.get_monitor_at(snap_x, snap_y)
                        mon_top = cur_mon.top if cur_mon else 0
                        mon_bottom = cur_mon.bottom if cur_mon else self.mouse.vh

                        is_edge_scrolling = self.edge_scrolling.update(
                            cursor_x=snap_x,
                            cursor_y=snap_y,
                            monitor_top=mon_top,
                            monitor_bottom=mon_bottom,
                            now=t_now,
                        )

                        if is_edge_scrolling:
                            self.dwell_clicker.cancel()
                            self.hud.hide()
                        else:
                            # Valutazione Sicurezza Dwell su Aree Critiche
                            _, eff_dwell = self.dwell_safety.evaluate_dwell_time(snap_x, snap_y, self._base_dwell_time)
                            if self.dwell_clicker.dwell_time != eff_dwell:
                                self.dwell_clicker.dwell_time = eff_dwell
                            self.dwell_clicker.update(snap_x, snap_y, t_now)

                with self.telemetry_lock:
                    self.shared_fps = loop_fps
                    self.shared_face_detected = face_detected
                    self.shared_is_blinking = is_blinking
                    self.shared_yaw = yaw
                    self.shared_pitch = pitch
                    self.shared_roll = roll
                    self.shared_raw_x = raw_x
                    self.shared_raw_y = raw_y
                    self.shared_is_copilot = self.copilot.is_currently_overridden
                    self.shared_is_snapped = self.magnetic_snapper.is_snapped

                time.sleep(0.016)
                continue

            # ---------------- MODALITÀ HARDWARE WEBCAM REALE ----------------
            ret, frame, timestamp, _ = self.camera.wait_for_frame(timeout=0.035)

            dt = t_now - last_loop_time
            if dt > 0:
                loop_fps = 0.9 * loop_fps + 0.1 * (1.0 / dt)
            last_loop_time = t_now

            raw_x, raw_y = 0.5, 0.5
            ergo_st = None
            if ret and frame is not None:
                res = self.tracker.process_frame(frame, timestamp_sec=t_now)
                face_detected = res.face_detected

                # Gestione Centratura Automatica su Rientro Volto (Auto-Recenter on Face Re-Engagement)
                if not face_detected:
                    if not self.was_face_lost:
                        self.was_face_lost = True
                        self.face_lost_timestamp = t_now
                        self.face_stable_since = 0.0
                        self.stable_reference_pose = None
                else:
                    if self.was_face_lost:
                        time_lost = t_now - self.face_lost_timestamp
                        if time_lost >= 3.0 and self.auto_recenter_enabled:
                            if self.face_stable_since == 0.0:
                                self.face_stable_since = t_now
                                self.stable_reference_pose = (res.yaw, res.pitch)
                            else:
                                ref_y, ref_p = self.stable_reference_pose
                                if abs(res.yaw - ref_y) < 2.5 and abs(res.pitch - ref_p) < 2.5:
                                    if t_now - self.face_stable_since >= 1.5:
                                        self.recenter()
                                        self.audio_feedback.play("resume")
                                        self.was_face_lost = False
                                        self.face_stable_since = 0.0
                                        self.stable_reference_pose = None
                                else:
                                    self.face_stable_since = t_now
                                    self.stable_reference_pose = (res.yaw, res.pitch)
                        else:
                            self.was_face_lost = False
                is_blinking = res.is_blinking
                yaw = res.yaw
                pitch = res.pitch
                roll = res.roll
                raw_x = res.cursor_raw_x
                raw_y = res.cursor_raw_y
                raw_y, is_jolt = self.wheelchair_jolt.filter_y(raw_y, t_now)
                if is_jolt:
                    if self.dwell_clicker.progress > 0.0:
                        self.dwell_clicker.cancel()
                        self.clinical_logger.record_dwell_aborted()
                    self.clinical_logger.record_wheelchair_jolt()

                if face_detected:
                    ergo_st = self.ergonomics_monitor.update(yaw, pitch, roll, now=t_now)
                    if ergo_st:
                        self.tracker.set_adaptive_bias(ergo_st.yaw_bias_compensation, ergo_st.pitch_bias_compensation)
                        if ergo_st.is_new_fatigue_alert:
                            self.clinical_logger.record_ergonomic_alert(ergo_st.fatigue_reason)
                    if not self.is_paused:
                        self.gesture_trigger.process_blendshapes(
                            jaw_open_score=res.jaw_open_score,
                            smile_score=res.smile_score,
                            brow_down_score=res.brow_down_score,
                            now=t_now,
                        )

                # Freno di emergenza fisiologico: chiusura volontaria degli occhi annulla istantaneamente il Dwell o Drag in corso
                if face_detected and is_blinking:
                    if self.mouse.is_dragging:
                        self.mouse.mouse_up("left")
                    if self.dwell_clicker.progress > 0.0:
                        self.clinical_logger.record_dwell_aborted()
                        self.dwell_clicker.cancel()

                # Iniezione mouse e Clic a sosta eseguiti SOLO se armato (non in pausa)
                if face_detected and not is_blinking and not self.is_paused:
                    norm_x, norm_y = self.ballistics.compute_normalized_xy(
                        raw_x, raw_y, self.gain_x_left, self.gain_x_right, self.gain_y_up, self.gain_y_down, now=t_now
                    )

                    target_px = self.mouse.vx + norm_x * self.mouse.vw
                    target_py = self.mouse.vy + norm_y * self.mouse.vh

                    filt_x, filt_y = self.dsp_filter.filter(target_px, target_py, t_now)
                    atax_x, atax_y, _ = self.ataxia_damper.process(filt_x, filt_y, t_now)
                    clamped_x, clamped_y, is_spasm = self.spasm_clamp.clamp(atax_x, atax_y, t_now)
                    if is_spasm:
                        if self.dwell_clicker.progress > 0.0:
                            self.dwell_clicker.cancel()
                            self.clinical_logger.record_dwell_aborted()
                        self.clinical_logger.record_spasm_shock()
                        self.clinical_logger.record_dystonic_teleport_clamped()
                    snap_x, snap_y = self.magnetic_snapper.apply_snap(clamped_x, clamped_y, t_now)

                    act_x, act_y = self.mouse.get_cursor_pos()
                    is_overridden = self.copilot.check_override(act_x, act_y, t_now)
                    if not is_overridden:
                        self.mouse.move_to_pixel(snap_x, snap_y)
                        self.copilot.record_injection(snap_x, snap_y)
                        self.clinical_logger.record_cursor_movement(snap_x, snap_y)

                        # Gestione Scorrimento Continuo ai Bordi (Edge Scrolling)
                        mon_top, mon_bottom = self.mouse.vy, self.mouse.vy + self.mouse.vh
                        is_edge_scrolling = self.edge_scrolling.update(
                            cursor_y=snap_y,
                            monitor_top=mon_top,
                            monitor_bottom=mon_bottom,
                            now=t_now,
                        )

                        if is_edge_scrolling:
                            self.dwell_clicker.cancel()
                            self.hud.hide()
                        else:
                            # Valutazione Sicurezza Dwell su Aree Critiche
                            _, eff_dwell = self.dwell_safety.evaluate_dwell_time(snap_x, snap_y, self._base_dwell_time)
                            if self.dwell_clicker.dwell_time != eff_dwell:
                                self.dwell_clicker.dwell_time = eff_dwell
                            self.dwell_clicker.update(snap_x, snap_y, t_now)

            with self.telemetry_lock:
                self.shared_fps = self.camera.actual_fps if self.camera.actual_fps > 0 else loop_fps
                self.shared_luma = self.camera.current_luma
                self.shared_mic_vol = self.acoustic.current_volume
                self.shared_face_detected = face_detected
                self.shared_is_blinking = is_blinking
                self.shared_yaw = yaw
                self.shared_pitch = pitch
                self.shared_roll = roll
                self.shared_is_fatigued = ergo_st.is_fatigued if ergo_st else False
                self.shared_fatigue_reason = ergo_st.fatigue_reason if ergo_st else "Nessuna"
                self.shared_is_snapped = self.magnetic_snapper.is_snapped
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
            is_fatigued = self.shared_is_fatigued
            fatigue_reason = self.shared_fatigue_reason
            is_copilot = self.shared_is_copilot
            self.shared_hud_dirty = False

        if self.is_paused or is_copilot or not self.dwell_clicker.is_enabled:
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
            is_fatigued=is_fatigued,
            fatigue_reason=fatigue_reason,
            is_copilot=is_copilot,
        )

        self.root.after(33, self._gui_update_loop)

    def on_close(self, confirm: bool = True):
        """
        Spegnimento pulito e rilascio delle risorse con salvaguardia anti-chiusura accidentale.
        Se l'utente o il caregiver preme accidentalmente la 'X' della finestra,
        viene offerta la scelta di minimizzare mantenendo il controllo attivo,
        oppure di uscire definitivamente.
        """
        if confirm and not self.force_demo:
            try:
                from tkinter import messagebox
                res = messagebox.askyesno(
                    "SteadyMotion AI - Conferma Uscita",
                    "SteadyMotion AI è attualmente in esecuzione con controllo del cursore attivo.\n\n"
                    "Vuoi davvero chiudere definitivamente il software?\n\n"
                    "• Premi 'SÌ' per arrestare il tracciamento e chiudere l'applicazione.\n"
                    "• Premi 'NO' per minimizzare la finestra e continuare a usare il puntatore.",
                )
                if not res:
                    self.root.iconify()
                    return
            except Exception:
                pass

        self.is_running = False
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=1.0)
        if self.mouse.is_dragging:
            self.mouse.mouse_up("left")
        disable_high_precision_timer()
        self.copilot.stop_hook()
        self.magnetic_snapper.close()
        self.audio_feedback.stop()
        self.camera.stop()
        self.acoustic.stop()
        self.hud.hide()
        try:
            self.clinical_logger.save_report(patient_id="Paziente-01")
        except Exception:
            pass
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
    if len(sys.argv) > 1 and any(arg in sys.argv for arg in ("--diagnostics", "--diag", "-d")):
        from core.diagnostics import run_full_diagnostics, format_diagnostic_report_text
        print("\n" + "=" * 60)
        print("  Avvio Diagnostica Hardware SteadyMotion AI...")
        print("  Scansione webcam USB, misura FPS reali e rumore audio in corso...")
        print("=" * 60 + "\n")
        diag = run_full_diagnostics()
        report = format_diagnostic_report_text(diag)
        print(report)
        report_path = "report_diagnostica_hardware.txt"
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)
            print(f"\n[OK] Report salvato con successo in: {os.path.abspath(report_path)}")
        except Exception as e:
            print(f"\n[ATTENZIONE] Impossibile salvare il file di report: {e}")
        print("\nPremere Invio per uscire...")
        try:
            input()
        except Exception:
            pass
        sys.exit(0)

    is_demo = "--demo" in sys.argv
    app = SteadyMotionApp(force_demo=is_demo)
    app.start()
