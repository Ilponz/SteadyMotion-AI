"""
Macchina a stati per Dwell Click (Clic a Sosta Temporizzata).
Consente l'attivazione del mouse mediante stazionamento del puntatore
all'interno di un raggio di tolleranza per un tempo predefinito (es. 600 ms).
"""

import math
import time
from typing import Callable, Optional, Tuple


class DwellClicker:
    """
    Gestore del Clic a Sosta con isteresi spaziale e temporale.
    """

    def __init__(
        self,
        dwell_time: float = 0.65,
        tolerance_radius: float = 24.0,
        cooldown_time: float = 0.40,
        click_callback: Optional[Callable[[str, int, int], None]] = None,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
    ):
        self.dwell_time = dwell_time
        self.tolerance_radius = tolerance_radius
        self.cooldown_time = cooldown_time

        self.click_callback = click_callback
        self.progress_callback = progress_callback

        self.current_action = "left"  # "left", "right", "double", "drag"
        self.is_enabled = True

        self.anchor_x: Optional[float] = None
        self.anchor_y: Optional[float] = None
        self.start_time: Optional[float] = None
        self.last_click_time: float = 0.0
        self.is_dwelling = False
        self.has_fired = False

    def set_action(self, action: str):
        """Imposta l'azione eseguita al termine del dwell ('left', 'right', 'double', 'drag')."""
        self.current_action = action

    def update(self, x: float, y: float, now: Optional[float] = None) -> float:
        """
        Aggiorna la posizione del cursore e calcola il progresso di dwell.
        Restituisce un valore tra 0.0 (nessun dwell) e 1.0 (clic imminente/eseguito).
        """
        if not self.is_enabled:
            return 0.0

        if now is None:
            now = time.perf_counter()

        # Cooldown dopo l'ultimo clic
        if now - self.last_click_time < self.cooldown_time:
            return 0.0

        # Se non abbiamo un'ancora attiva, inizializziamo
        if self.anchor_x is None or self.anchor_y is None:
            self.anchor_x = x
            self.anchor_y = y
            self.start_time = now
            self.has_fired = False
            self.is_dwelling = True
            return 0.0

        dist = math.hypot(x - self.anchor_x, y - self.anchor_y)

        if dist > self.tolerance_radius:
            # Il cursore è uscito dalla zona di sosta: reset dell'ancora
            self.anchor_x = x
            self.anchor_y = y
            self.start_time = now
            self.has_fired = False
            self.is_dwelling = True
            if self.progress_callback:
                self.progress_callback(0.0, int(x), int(y))
            return 0.0

        # Il cursore è all'interno della zona di sosta
        if self.has_fired:
            # Ha già cliccato e non si è ancora spostato fuori
            return 0.0

        elapsed = now - self.start_time
        progress = min(1.0, elapsed / self.dwell_time)

        if self.progress_callback:
            self.progress_callback(progress, int(self.anchor_x), int(self.anchor_y))

        if progress >= 1.0 and not self.has_fired:
            self.has_fired = True
            self.last_click_time = now
            if self.click_callback:
                self.click_callback(self.current_action, int(self.anchor_x), int(self.anchor_y))
            # Se era un'azione speciale monouso, resetta a "left"
            if self.current_action in ("right", "double"):
                self.current_action = "left"

        return progress

    def cancel(self):
        """Annulla il conteggio attuale."""
        self.anchor_x = None
        self.anchor_y = None
        self.start_time = None
        self.has_fired = False
        self.is_dwelling = False
        if self.progress_callback:
            self.progress_callback(0.0, 0, 0)
