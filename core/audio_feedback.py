"""
Modulo di Feedback Uditivo Multi-Sensoriale per Clic & Dwell (Audio Feedback Engine).
Progettato per pazienti con disabilità motoria e ipovisione:
1. Emette segnali acustici chiari, immediati e non invasivi al verificarsi degli eventi del mouse.
2. Coda eventi asincrona non-bloccante (< 0.05 ms in tracking loop a 60-120 Hz).
3. Pre-sintesi in RAM a zero-allocazioni di campioni audio PCM 16-bit Mono (RIFF/WAVE)
   con inviluppo sinusoidale rialzato (Hann window) a 3.5 ms:
   - Elimina radicalmente le armoniche spurie e i 'click/pop' fastidiosi delle onde quadre di sistema (winsound.Beep).
   - Previene l'affaticamento acustico e le crisi di iperacusia comuni in SLA/Atassia.
4. Gestione dinamica priorità & Time-To-Live (TTL):
   - I micro-tick del dwell scadono a 50 ms (zero stale clicks).
   - I clic ordinari scadono a 250 ms.
   - L'allarme caregiver svuota la coda a priorità assoluta per un intervento immediato.
"""

import math
import queue
import struct
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import winsound
    HAS_WINSOUND = True
except Exception:
    HAS_WINSOUND = False


def synthesize_sinusoidal_wav(
    tones: List[Tuple[int, int]],
    sample_rate: int = 22050,
    volume: float = 0.45,
    inter_tone_silence_ms: float = 20.0,
) -> bytes:
    """
    Sintetizza in RAM un buffer audio conforme allo standard RIFF/WAVE PCM 16-bit Mono.
    Applica un inviluppo Hann (raised-cosine) da 3.5 ms all'attacco e al decadimento di ogni tono,
    eliminando le armoniche distorcenti e i rumori impulsivi.
    """
    if not tones:
        return b""

    pcm = bytearray()
    fade_samples = max(4, int(sample_rate * 0.0035))  # 3.5 ms smoothing

    for idx, (freq, dur_ms) in enumerate(tones):
        if idx > 0 and inter_tone_silence_ms > 0:
            silence_samples = int(sample_rate * (inter_tone_silence_ms / 1000.0))
            pcm.extend(b"\x00" * (silence_samples * 2))

        n_samples = int(sample_rate * (dur_ms / 1000.0))
        if n_samples <= 0 or freq <= 0:
            continue

        amp = int(32767 * max(0.0, min(1.0, volume)))
        omega = 2.0 * math.pi * float(freq) / float(sample_rate)

        for i in range(n_samples):
            if i < fade_samples:
                env = 0.5 * (1.0 - math.cos(math.pi * i / fade_samples))
            elif i > n_samples - fade_samples:
                env = 0.5 * (1.0 - math.cos(math.pi * (n_samples - i) / fade_samples))
            else:
                env = 1.0

            val = int(amp * env * math.sin(omega * i))
            val = max(-32768, min(32767, val))
            pcm.extend(struct.pack("<h", val))

    if not pcm:
        return b""

    data_len = len(pcm)
    riff_len = 36 + data_len
    byte_rate = sample_rate * 2
    block_align = 2
    bits_per_sample = 16

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        riff_len,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_len,
    )
    return bytes(header + pcm)


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
            "alarm": [(1760, 120), (2200, 160), (1760, 120), (2640, 250)],
            "dwell_tick": [(1500, 10)],
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
            "alarm": [(660, 150), (880, 200), (660, 150), (1100, 250)],
            "dwell_tick": [(600, 12)],
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
            "alarm": [(2000, 150), (2800, 200), (2000, 150), (3200, 300)],
            "dwell_tick": [(2200, 15)],
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
            "alarm": [(1400, 80), (1800, 100), (1400, 80), (2200, 150)],
            "dwell_tick": [(1200, 8)],
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
        self._queue: queue.Queue = queue.Queue(maxsize=15)
        self._is_running = True
        self._pcm_cache: Dict[str, Dict[str, bytes]] = {}
        self._precompute_pcm_cache()

        if HAS_WINSOUND:
            self._worker_thread = threading.Thread(
                target=self._audio_worker,
                daemon=True,
                name="AudioFeedbackWorker",
            )
            self._worker_thread.start()

    def _precompute_pcm_cache(self):
        """Pre-sintetizza in RAM tutti i campioni audio WAV dei soundpack a zero allocazioni dinamiche a runtime."""
        for sp_id, sp in SOUNDPACKS.items():
            self._pcm_cache[sp_id] = {}
            for st, tones in sp["tones"].items():
                self._pcm_cache[sp_id][st] = synthesize_sinusoidal_wav(tones)

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

    def play_alarm(self):
        """Emette la sequenza bitonale urgente per la chiamata caregiver, svuotando code pregresse."""
        if not self.is_enabled or not HAS_WINSOUND or self.soundpack_id == "mute":
            return
        # Preemption: svuota eventi minori pendenti per non ritardare l'allarme
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Exception:
                break
        t_now = time.perf_counter()
        try:
            self._queue.put_nowait(("alarm", t_now))
        except queue.Full:
            pass

    def play(self, sound_type: str = "click_left"):
        """Accoda la richiesta sonora con timestamp TTL senza bloccare il thread chiamante."""
        if not self.is_enabled or not HAS_WINSOUND or self.soundpack_id == "mute":
            return
        t_now = time.perf_counter()
        try:
            self._queue.put_nowait((sound_type, t_now))
        except queue.Full:
            pass

    def get_precomputed_wav(self, sound_type: str, soundpack_id: Optional[str] = None) -> Optional[bytes]:
        """Restituisce il buffer PCM WAV pre-sintetizzato in memoria."""
        sp = soundpack_id or self.soundpack_id
        return self._pcm_cache.get(sp, {}).get(sound_type)

    def _audio_worker(self):
        while self._is_running:
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                if isinstance(item, tuple):
                    sound_type, enqueue_time = item
                else:
                    sound_type = item
                    enqueue_time = time.perf_counter()

                now = time.perf_counter()
                age = now - enqueue_time

                # Filtro di obsolescenza (TTL Guard): previene la riproduzione tardiva e desincronizzata
                if sound_type == "dwell_tick" and age > 0.050:
                    continue
                elif sound_type != "alarm" and age > 0.250:
                    continue

                # 1. Tentativo di riproduzione WAV sinusoidale smooth da cache RAM
                played = False
                wav_data = self._pcm_cache.get(self.soundpack_id, {}).get(sound_type)
                if wav_data and HAS_WINSOUND:
                    try:
                        winsound.PlaySound(wav_data, winsound.SND_MEMORY)
                        played = True
                    except Exception:
                        played = False

                # 2. Fallback su Beep standard se PlaySound fallisce
                if not played and HAS_WINSOUND:
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
