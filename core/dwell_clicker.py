"""
Dwell Clicker con accumulatore Leaky Bucket e Gravity Well.
Progettato specificamente per utenti affetti da tremore patologico o spasmi involontari:
se durante la sosta (es. a 550 ms su 650 ms) un picco di tremore sposta brevemente il cursore
oltre la soglia, il progresso NON viene azzerato istantaneamente, ma rallenta o decade dolcemente.
Questo permette di completare il clic senza la frustrazione del reset continuo.
"""

import math
import time
from typing import Callable, Optional, Tuple


class DwellClicker:
    """Motore di Clic a Sosta con tolleranza elastica al tremore (Leaky Bucket)."""

    def __init__(
        self,
        dwell_time: float = 0.65,
        tolerance_radius: float = 24.0,
        cooldown_time: float = 0.40,
        leak_rate: float = 1.2,  # Velocità di decadimento quando si è fuori tolleranza
        click_callback: Optional[Callable[[str, int, int], None]] = None,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
    ):
        self.dwell_time = dwell_time
        self.tolerance_radius = tolerance_radius
        self.grace_radius = tolerance_radius * 1.8  # Oltre questa soglia è uno spostamento intenzionale
        self.cooldown_time = cooldown_time
        self.leak_rate = leak_rate

        self.click_callback = click_callback
        self.progress_callback = progress_callback

        self.current_action = "left"
        self.is_enabled = True

        self.anchor_x: Optional[float] = None
        self.anchor_y: Optional[float] = None
        self.progress: float = 0.0
        self.last_update_time: Optional[float] = None
        self.last_click_time: float = 0.0
        self.has_fired: bool = False

    def set_action(self, action: str):
        self.current_action = action

    def update(self, x: float, y: float, now: Optional[float] = None) -> float:
        if not self.is_enabled:
            return 0.0

        if now is None:
            now = time.perf_counter()

        # Cooldown di riposo dopo un clic avvenuto
        if now - self.last_click_time < self.cooldown_time:
            return 0.0

        if self.last_update_time is None:
            self.last_update_time = now
            dt = 0.016
        else:
            dt = max(0.001, min(0.1, now - self.last_update_time))
            self.last_update_time = now

        # Inizializzazione prima ancora
        if self.anchor_x is None or self.anchor_y is None:
            self.anchor_x = x
            self.anchor_y = y
            self.progress = 0.0
            self.has_fired = False
            return 0.0

        dist = math.hypot(x - self.anchor_x, y - self.anchor_y)

        if dist >= self.grace_radius:
            # Spostamento volontario verso un'altra icona: reset totale
            self.anchor_x = x
            self.anchor_y = y
            self.progress = 0.0
            self.has_fired = False
            if self.progress_callback:
                self.progress_callback(0.0, int(x), int(y))
            return 0.0

        if self.has_fired:
            # Attendiamo che l'utente esca prima di un nuovo clic
            return 0.0

        if dist <= self.tolerance_radius:
            # Il puntatore è fermo nell'area bersaglio: accumula progresso
            self.progress = min(1.0, self.progress + (dt / self.dwell_time))
        else:
            # Il cursore è nella 'Grace Zone' (micro-tremore transitorio):
            # decade lentamente invece di azzerarsi a 0.0
            self.progress = max(0.0, self.progress - (dt * self.leak_rate / self.dwell_time))

        if self.progress_callback:
            self.progress_callback(self.progress, int(self.anchor_x), int(self.anchor_y))

        # Attivazione del clic al 100%
        if self.progress >= 1.0 and not self.has_fired:
            self.has_fired = True
            self.last_click_time = now
            self.progress = 0.0
            if self.click_callback:
                self.click_callback(self.current_action, int(self.anchor_x), int(self.anchor_y))
            if self.current_action in ("right", "double"):
                self.current_action = "left"

        return self.progress

    def cancel(self):
        last_x = int(self.anchor_x) if self.anchor_x is not None else 0
        last_y = int(self.anchor_y) if self.anchor_y is not None else 0
        self.anchor_x = None
        self.anchor_y = None
        self.progress = 0.0
        self.has_fired = False
        self.last_update_time = None
        if self.progress_callback:
            self.progress_callback(0.0, last_x, last_y)
