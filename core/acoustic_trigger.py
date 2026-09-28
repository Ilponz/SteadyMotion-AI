"""
Trigger acustico opzionale (Microfono Webcam - Costo 0 €).
Ispirato all'architettura di Talon Voice: rileva suoni non verbali impulsivi
(schiocco di lingua 'pop', soffio d'aria 'puff') e scatena il clic istantaneo,
eliminando ogni affaticamento muscolare per utenti con mobilità facciale ridotta.
"""

import threading
import time
from typing import Callable, Optional
import numpy as np

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


class AcousticTrigger:
    """Rilevatore di impulsi sonori RMS a latenza ultra-bassa."""

    def __init__(
        self,
        threshold: float = 0.15,
        debounce_time: float = 0.35,
        callback: Optional[Callable[[], None]] = None,
        sample_rate: int = 16000,
        chunk_size: int = 512,
    ):
        self.threshold = threshold
        self.debounce_time = debounce_time
        self.callback = callback
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

        self.is_running = False
        self.stream = None
        self.last_trigger_time = 0.0
        self.current_volume = 0.0

    def start(self) -> bool:
        if not SOUNDDEVICE_AVAILABLE:
            return False

        try:
            self.is_running = True
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            )
            self.stream.start()
            return True
        except Exception:
            self.is_running = False
            return False

    def _audio_callback(self, indata, frames, time_info, status):
        if not self.is_running:
            return

        # Calcolo dell'energia RMS
        rms = float(np.sqrt(np.mean(indata**2)))
        self.current_volume = rms

        now = time.perf_counter()
        if rms > self.threshold and (now - self.last_trigger_time > self.debounce_time):
            self.last_trigger_time = now
            if self.callback:
                self.callback()

    def stop(self):
        self.is_running = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
