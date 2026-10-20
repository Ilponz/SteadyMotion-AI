"""
Modulo Trigger Gesti Facciali Silenziosi (Facial Gesture Clicker).
Progettato per SteadyMotion AI v3.0.

Obiettivo Clinico:
Consentire a pazienti impossibilitati ad attendere il dwell time (650 ms)
o incapaci di emettere suoni (pazienti tracheostomizzati, ventilati, o in ambienti rumorosi)
di eseguire clic istantanei e silenziosi tramite micro-gesti del viso:
1. "jaw_open" (apertura mandibola / bocca)
2. "smile" (sorriso / trazione commissurale labiale)
3. "brow_down" (corrugamento sopraccigliare)

Principio di Funzionamento:
- Filtro a isteresi: soglia di attivazione (default 0.45) e soglia di rilascio (default 0.20)
  per prevenire clic multipli involontari o tremolio muscolare.
- Debounce temporale configurabile (default 0.45s).
- Zero allocazioni heap a 60 Hz.
"""

import time
from typing import Callable, Dict, Optional


class GestureTrigger:
    """Riconoscitore di gesti facciali FACS a isteresi per clic istantaneo silenzioso."""

    SUPPORTED_GESTURES = ("jaw_open", "smile", "brow_down")

    def __init__(
        self,
        gesture_type: str = "jaw_open",
        trigger_threshold: float = 0.45,
        release_threshold: float = 0.20,
        debounce_sec: float = 0.45,
        click_callback: Optional[Callable[[str], None]] = None,
        is_enabled: bool = False,
    ):
        self.gesture_type = gesture_type if gesture_type in self.SUPPORTED_GESTURES else "jaw_open"
        self.trigger_threshold = float(trigger_threshold)
        self.release_threshold = float(release_threshold)
        self.debounce_sec = float(debounce_sec)
        self.click_callback = click_callback
        self.is_enabled = bool(is_enabled)

        # Stato interno
        self.is_primed: bool = True  # Pronto ad attivare il trigger
        self.last_trigger_time: float = 0.0
        self.current_score: float = 0.0

    def update_params(
        self,
        is_enabled: Optional[bool] = None,
        gesture_type: Optional[str] = None,
        trigger_threshold: Optional[float] = None,
        release_threshold: Optional[float] = None,
        debounce_sec: Optional[float] = None,
    ):
        """Aggiorna i parametri operativi in tempo reale."""
        if is_enabled is not None:
            self.is_enabled = bool(is_enabled)
        if gesture_type is not None and gesture_type in self.SUPPORTED_GESTURES:
            self.gesture_type = gesture_type
        if trigger_threshold is not None:
            self.trigger_threshold = float(trigger_threshold)
        if release_threshold is not None:
            self.release_threshold = float(release_threshold)
        if debounce_sec is not None:
            self.debounce_sec = float(debounce_sec)

    def process_blendshapes(
        self,
        jaw_open_score: float,
        smile_score: float,
        brow_down_score: float,
        now: Optional[float] = None,
    ) -> bool:
        """
        Elabora i punteggi FACS del frame corrente.
        Restituisce True se è scattato un clic.
        """
        if not self.is_enabled:
            return False

        if now is None:
            now = time.perf_counter()

        # Selezione punteggio in base al gesto configurato
        if self.gesture_type == "jaw_open":
            score = float(jaw_open_score)
        elif self.gesture_type == "smile":
            score = float(smile_score)
        elif self.gesture_type == "brow_down":
            score = float(brow_down_score)
        else:
            score = float(jaw_open_score)

        self.current_score = score

        # 1. Riarmo a soglia bassa (Hysteresis Release)
        if score <= self.release_threshold:
            self.is_primed = True
            return False

        # 2. Controllo attivazione su superamento soglia alta
        if self.is_primed and score >= self.trigger_threshold:
            if (now - self.last_trigger_time) >= self.debounce_sec:
                self.is_primed = False
                self.last_trigger_time = now
                if self.click_callback:
                    self.click_callback(self.gesture_type)
                return True

        return False
