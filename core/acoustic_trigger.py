"""
Trigger acustico opzionale con Noise Floor Calibration adattiva.
Ispirato all'architettura di Talon Voice: rileva suoni non verbali impulsivi
(schiocco di lingua 'pop', soffio d'aria 'puff') e scatena il clic istantaneo,
eliminando ogni affaticamento muscolare per utenti con mobilità facciale ridotta.

Ottimizzazioni per ambienti reali:
1. Auto-calibrazione del rumore di fondo (Noise Floor):
   campiona l'RMS della stanza ed imposta automaticamente la soglia ideale a SNR controllato.
2. Filtro passa-alto di pre-enfasi per eliminare ronzii e voci continue (< 1000 Hz).
3. Zero-Crossing Rate (ZCR) per identificare con precisione la firma spettrale impulsiva.
"""

import threading
import time
from typing import Callable, List, Optional
import numpy as np

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


class AcousticTrigger:
    """Rilevatore di impulsi sonori RMS a latenza ultra-bassa con calibrazione adattiva."""

    def __init__(
        self,
        threshold: float = 0.18,
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
        self.is_enabled = True
        self.stream = None
        self.last_trigger_time = 0.0
        self.current_volume = 0.0
        self.noise_floor = 0.04

        # Stato di calibrazione adattiva
        self.is_calibrating = False
        self._calib_samples: List[float] = []
        self._calib_end_time = 0.0
        self._calib_callback: Optional[Callable[[float], None]] = None

    def start(self) -> bool:
        if not SOUNDDEVICE_AVAILABLE:
            return False

        try:
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

    def update_params(self, enabled: bool, threshold: float):
        self.is_enabled = enabled
        self.threshold = max(0.01, threshold)

    def start_auto_calibration(self, duration: float = 2.0, on_complete: Optional[Callable[[float], None]] = None):
        """Avvia il campionamento per determinare il rumore di fondo della stanza e la soglia ottima."""
        if not self.is_running:
            self.start()
        self._calib_samples = []
        self._calib_end_time = time.perf_counter() + duration
        self._calib_callback = on_complete
        self.is_calibrating = True

    def _audio_callback(self, indata, frames, time_info, status):
        if not self.is_running or not self.is_enabled or indata.shape[0] == 0:
            return

        signal = indata[:, 0]
        # Pre-enfasi: filtro passa-alto differenziale per sopprimere ronzii e parlato ordinario
        hp_signal = np.diff(signal, prepend=signal[0])
        hp_rms = float(np.sqrt(np.mean(hp_signal**2)))
        self.current_volume = hp_rms

        # Auto-calibrazione in corso: accumulo campioni rumore ambiente
        if self.is_calibrating:
            self._calib_samples.append(hp_rms)
            if time.perf_counter() >= self._calib_end_time:
                self.is_calibrating = False
                if self._calib_samples:
                    self.noise_floor = float(np.mean(self._calib_samples))
                    # Calcolo soglia operativa con margine SNR sicuro
                    new_thresh = max(0.08, min(0.38, self.noise_floor * 2.2 + 0.04))
                    self.threshold = round(new_thresh, 3)
                    if self._calib_callback:
                        cb = self._calib_callback
                        self._calib_callback = None
                        cb(self.threshold)
            return

        # Zero-Crossing Rate per discriminare transitori rapidi (soffio o schiocco 'pop')
        zcr = float(np.mean(np.abs(np.diff(np.sign(signal))))) / 2.0

        now = time.perf_counter()
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
