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
from typing import Any, Dict, List, Optional, Tuple

try:
    import winsound
    HAS_WINSOUND = True
except Exception:
    HAS_WINSOUND = False

# Pacchetti Sonori Clinici Differenziati
SOUNDPACKS: Dict[str, Dict[str, Any]] = {
    "standard": {
        "name": "Standard (Bilanciato)",
        "tones": {
            "click_left": [(1200, 35)],
            "click_right": [(1800, 45)],
            "double_click": [(1300, 25), (1600, 30)],
            "drag_start": [(900, 30), (1300, 35)],
            "drag_end": [(1300, 30), (900, 35)],
            "pause": [(700, 50)],
            "resume": [(1100, 40)],
        },
    },
    "mellow": {
        "name": "Morbido / Grave (Iperacusia)",
        "tones": {
            "click_left": [(520, 35)],
            "click_right": [(680, 40)],
            "double_click": [(520, 25), (650, 30)],
            "drag_start": [(440, 35), (550, 35)],
            "drag_end": [(550, 35), (440, 35)],
            "pause": [(380, 50)],
            "resume": [(500, 40)],
        },
    },
    "high_contrast": {
        "name": "Alto Contrasto (Ambienti Rumorosi)",
        "tones": {
            "click_left": [(1600, 50)],
            "click_right": [(2400, 60)],
            "double_click": [(1600, 30), (2200, 35)],
            "drag_start": [(1200, 40), (1800, 45)],
            "drag_end": [(1800, 40), (1200, 45)],
            "pause": [(900, 60)],
            "resume": [(1500, 50)],
        },
    },
    "subtle": {
        "name": "Subtle / Discreto",
        "tones": {
            "click_left": [(1000, 15)],
            "click_right": [(1400, 20)],
            "double_click": [(1000, 15), (1300, 15)],
            "drag_start": [(800, 20), (1100, 20)],
            "drag_end": [(1100, 20), (800, 20)],
            "pause": [(600, 30)],
            "resume": [(900, 25)],
        },
    },
    "mute": {
        "name": "Silenzioso (Muto)",
        "tones": {},
    },
}


class AudioFeedback:
    """Motore di feedback acustico asincrono nativo Win32 con Soundpack clinici."""

    def __init__(self, enabled: bool = True, soundpack: str = "standard"):
        self.is_enabled = enabled
        self.soundpack_id = soundpack if soundpack in SOUNDPACKS else "standard"
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

    def set_soundpack(self, soundpack_id: str) -> bool:
        """Imposta il pacchetto sonoro attivo."""
        if soundpack_id in SOUNDPACKS:
            self.soundpack_id = soundpack_id
            return True
        return False

    @staticmethod
    def get_available_soundpacks() -> List[Tuple[str, str]]:
        """Restituisce l'elenco dei soundpack clinici disponibili (id, display_name)."""
        return [(k, v["name"]) for k, v in SOUNDPACKS.items()]

    def play(self, sound_type: str = "click_left"):
        """Accoda la richiesta sonora senza bloccare il thread chiamante."""
        if not self.is_enabled or not HAS_WINSOUND or self.soundpack_id == "mute":
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
                sp = SOUNDPACKS.get(self.soundpack_id, SOUNDPACKS["standard"])
                tones = sp["tones"].get(sound_type, [])
                for idx, (freq, dur) in enumerate(tones):
                    if idx > 0:
                        time.sleep(0.03)
                    winsound.Beep(freq, dur)
            except Exception:
                pass
            finally:
                self._queue.task_done()

    def stop(self):
        self._is_running = False
