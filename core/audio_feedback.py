"""
Modulo di Feedback Uditivo Multi-Sensoriale per Clic & Dwell (Audio Feedback Engine).
Progettato per pazienti con disabilità motoria e ipovisione:
1. Emette segnali acustici chiari, immediati e non invasivi al verificarsi degli eventi del mouse.
2. Coda eventi asincrona non-bloccante (zero frame persi nel tracking loop a 60 Hz).
3. Toni differenziati a livello frequenziale:
   - Clic Sinistro: Beep 1200 Hz (35 ms)
   - Clic Destro: Beep 1800 Hz (45 ms)
   - Doppio Clic: Doppio impulso rapido
   - Trascina (Drag Start / End): Tono ascendente / discendente
   - Pausa / Ripresa: Indicatore di stato
"""

import queue
import threading
import time
from typing import Optional

try:
    import winsound
    HAS_WINSOUND = True
except Exception:
    HAS_WINSOUND = False


class AudioFeedback:
    """Motore di feedback acustico asincrono nativo Win32."""

    def __init__(self, enabled: bool = True):
        self.is_enabled = enabled
        self._queue: queue.Queue = queue.Queue(maxsize=10)
        self._is_running = True

        if HAS_WINSOUND:
            self._worker_thread = threading.Thread(
                target=self._audio_worker,
                daemon=True,
                name="AudioFeedbackWorker",
            )
            self._worker_thread.start()

    def set_enabled(self, enabled: bool):
        self.is_enabled = enabled

    def play(self, sound_type: str = "click_left"):
        """Accoda la richiesta sonora senza bloccare il thread chiamante."""
        if not self.is_enabled or not HAS_WINSOUND:
            return
        try:
            self._queue.put_nowait(sound_type)
        except queue.Full:
            pass

    def _audio_worker(self):
        while self._is_running:
            try:
                sound_type = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                if sound_type == "click_left":
                    winsound.Beep(1200, 35)
                elif sound_type == "click_right":
                    winsound.Beep(1800, 45)
                elif sound_type == "double_click":
                    winsound.Beep(1300, 25)
                    time.sleep(0.04)
                    winsound.Beep(1600, 30)
                elif sound_type == "drag_start":
                    winsound.Beep(900, 30)
                    winsound.Beep(1300, 35)
                elif sound_type == "drag_end":
                    winsound.Beep(1300, 30)
                    winsound.Beep(900, 35)
                elif sound_type == "pause":
                    winsound.Beep(700, 50)
                elif sound_type == "resume":
                    winsound.Beep(1100, 40)
            except Exception:
                pass
            finally:
                self._queue.task_done()

    def stop(self):
        self._is_running = False
