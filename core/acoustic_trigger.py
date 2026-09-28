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
            # Query del sample rate nativo del dispositivo per massima compatibilità hardware
            try:
                device_info = sd.query_devices(kind="input")
                if device_info and "default_samplerate" in device_info:
                    default_sr = int(device_info["default_samplerate"])
                    if default_sr > 0:
                        self.sample_rate = default_sr
            except Exception:
                pass

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
        if not self.is_running or indata.shape[0] == 0:
            return

        signal = indata[:, 0]
        # Pre-enfasi: filtro passa-alto differenziale del primo ordine per sopprimere ronzii e voce (<1000 Hz)
        hp_signal = np.diff(signal, prepend=signal[0])
        hp_rms = float(np.sqrt(np.mean(hp_signal**2)))
        self.current_volume = hp_rms

        # Zero-Crossing Rate (ZCR) per identificare transitori impulsivi tipici di pop e puff
        zcr = float(np.mean(np.abs(np.diff(np.sign(signal))))) / 2.0

        now = time.perf_counter()
        # Rileva solo se l'energia sulle alte frequenze supera la soglia e ha ZCR sufficiente
        if hp_rms > self.threshold and zcr > 0.08 and (now - self.last_trigger_time > self.debounce_time):
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
