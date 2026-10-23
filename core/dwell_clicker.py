"""
Dwell Clicker con accumulatore Leaky Bucket e Gravity Well.
Progettato specificamente per utenti affetti da tremore patologico o spasmi involontari:
1. Tolleranza elastica con Pozzo di Potenziale a Distanza Proporzionale (Soft Grace Zone):
   - Micro-tremore vicino al bordo (mu -> 0): decadimento rallentato (0.5x del base leak rate) per evitare frustrazione.
   - Spasmi muscolari bruschi o allontanamento (mu -> 1): decadimento accelerato (2.5x) per rapido spurgo.
2. Micro-Inseguimento Posturale Adattivo: all'interno del raggio di tolleranza, l'ancora segue
   i lentissimi scorrimenti posturali (< 4 px/s) evitando il fallimento del clic per affaticamento muscolare.
3. Ciclo di vita sicuro: disattivazione (is_enabled = False) con spurgo atomico immediato del progresso residuo.
4. Sincronizzazione clock cooldown: azzera salti fittizi di dt al risveglio dal cooldown.
5. Cancellazione atomica sicura priva di coordinate nulle fittizie (0, 0).
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
        leak_rate: float = 1.2,  # Velocità base di decadimento quando si è nella Grace Zone
        sweep_velocity_threshold: float = 240.0,  # Soglia di velocità transito per Anti-Sweep (px/s)
        spasm_velocity_threshold: float = 2200.0,  # Soglia picco spasmo acuto (px/s)
        click_callback: Optional[Callable[[str, int, int], None]] = None,
        progress_callback: Optional[Callable[[float, int, int], None]] = None,
        spasm_callback: Optional[Callable[[], None]] = None,
    ):
        self._dwell_time = max(0.1, float(dwell_time))
        self._tolerance_radius = max(5.0, float(tolerance_radius))
        self._grace_multiplier = 1.85
        self._grace_radius = self._tolerance_radius * self._grace_multiplier
        self.cooldown_time = max(0.0, float(cooldown_time))
        self.leak_rate = max(0.1, float(leak_rate))
        self.sweep_velocity_threshold = float(sweep_velocity_threshold)
        self.spasm_velocity_threshold = float(spasm_velocity_threshold)

        self.click_callback = click_callback
        self.progress_callback = progress_callback
        self.spasm_callback = spasm_callback

        self.current_action = "left"
        self._is_enabled = True

        self.anchor_x: Optional[float] = None
        self.anchor_y: Optional[float] = None
        self.progress: float = 0.0
        self.last_update_time: Optional[float] = None
        self.last_click_time: float = 0.0
        self.has_fired: bool = False

        self._prev_sample_x: Optional[float] = None
        self._prev_sample_y: Optional[float] = None
        self._prev_sample_time: Optional[float] = None

    @property
    def dwell_time(self) -> float:
        return self._dwell_time

    @dwell_time.setter
    def dwell_time(self, val: float):
        self._dwell_time = max(0.1, float(val))

    @property
    def tolerance_radius(self) -> float:
        return self._tolerance_radius

    @tolerance_radius.setter
    def tolerance_radius(self, val: float):
        self._tolerance_radius = max(5.0, float(val))
        self._grace_radius = self._tolerance_radius * self._grace_multiplier

    @property
    def grace_radius(self) -> float:
        return self._grace_radius

    @property
    def is_enabled(self) -> bool:
        return self._is_enabled

    @is_enabled.setter
    def is_enabled(self, val: bool):
        new_val = bool(val)
        if self._is_enabled and not new_val:
            self.cancel()
        self._is_enabled = new_val

    def set_action(self, action: str):
        self.current_action = action

    def update(self, x: float, y: float, now: Optional[float] = None) -> float:
        if not self._is_enabled:
            return 0.0

        if now is None:
            now = time.perf_counter()

        # Cooldown di riposo dopo un clic avvenuto: sincronizza il timer per prevenire picchi di dt al risveglio
        if now - self.last_click_time < self.cooldown_time:
            self.last_update_time = now
            return 0.0

        if self.last_update_time is None:
            self.last_update_time = now
            dt = 0.016
        else:
            dt = max(0.001, min(0.1, now - self.last_update_time))
            self.last_update_time = now

        # Calcolo velocità istantanea di transito
        instant_velocity = 0.0
        if self._prev_sample_x is not None and self._prev_sample_y is not None and self._prev_sample_time is not None:
            dt_sample = max(0.001, now - self._prev_sample_time)
            instant_velocity = math.hypot(x - self._prev_sample_x, y - self._prev_sample_y) / dt_sample

        self._prev_sample_x = x
        self._prev_sample_y = y
        self._prev_sample_time = now

        # 1. Rilevamento Spasmo Mioclonico Acuto (Spasm Shock)
        if instant_velocity >= self.spasm_velocity_threshold:
            self.cancel()
            if self.spasm_callback:
                self.spasm_callback()
            return 0.0

        # Inizializzazione prima ancora
        if self.anchor_x is None or self.anchor_y is None:
            self.anchor_x = x
            self.anchor_y = y
            self.progress = 0.0
            self.has_fired = False
            return 0.0

        dist = math.hypot(x - self.anchor_x, y - self.anchor_y)

        # 2. Anti-Sweep Velocity Gate: transito rapido tra target (nessun accumulo durante lo sweep)
        if instant_velocity >= self.sweep_velocity_threshold and (self.progress <= 0.05 or dist >= self._grace_radius):
            self.anchor_x = x
            self.anchor_y = y
            self.progress = 0.0
            self.has_fired = False
            if self.progress_callback:
                self.progress_callback(0.0, int(x), int(y))
            return 0.0

        if dist >= self._grace_radius:
            # Spostamento volontario verso un'altra icona: reset totale
            self.anchor_x = x
            self.anchor_y = y
            self.progress = 0.0
            self.has_fired = False
            if self.progress_callback:
                self.progress_callback(0.0, int(x), int(y))
            return 0.0

        if self.has_fired:
            # Attendiamo che l'utente esca dall'area di grace prima di consentire un nuovo clic
            return 0.0

        if dist <= self._tolerance_radius:
            # Il puntatore è fermo nell'area bersaglio: accumula progresso
            self.progress = min(1.0, self.progress + (dt / self._dwell_time))
            # Micro-adattamento per drift posturale lento
            self.anchor_x += (x - self.anchor_x) * min(0.1, dt * 2.0)
            self.anchor_y += (y - self.anchor_y) * min(0.1, dt * 2.0)
        else:
            # Soft Grace Zone (tolerance_radius < dist < grace_radius):
            # Pozzo di potenziale proporzionale alla distanza:
            # mu in [0, 1] esprime la prossimità al bordo esterno di fuga
            span = max(1.0, self._grace_radius - self._tolerance_radius)
            mu = min(1.0, max(0.0, (dist - self._tolerance_radius) / span))
            # Moltiplicatore dinamico: da 0.5x (micro-tremore al bordo) a 2.5x (spasmo in fuga)
            leak_multiplier = 0.5 + 2.0 * mu
            effective_leak = self.leak_rate * leak_multiplier
            self.progress = max(0.0, self.progress - (dt * effective_leak / self._dwell_time))
            if self.progress <= 0.0:
                self.progress = 0.0
                self.anchor_x = x
                self.anchor_y = y

        if self.progress_callback and self.anchor_x is not None and self.anchor_y is not None:
            self.progress_callback(self.progress, int(self.anchor_x), int(self.anchor_y))

        # Attivazione del clic al 100%
        if self.progress >= 1.0 and not self.has_fired:
            self.has_fired = True
            self.last_click_time = now
            fire_x = int(self.anchor_x)
            fire_y = int(self.anchor_y)
            self.progress = 0.0
            if self.click_callback:
                self.click_callback(self.current_action, fire_x, fire_y)
            if self.current_action in ("right", "double"):
                self.current_action = "left"

        return self.progress

    def cancel(self):
        last_x = int(self.anchor_x) if self.anchor_x is not None else -1
        last_y = int(self.anchor_y) if self.anchor_y is not None else -1
        self.anchor_x = None
        self.anchor_y = None
        self.progress = 0.0
        self.has_fired = False
        self.last_update_time = None
        self._prev_sample_time = None
        if self.progress_callback and last_x >= 0 and last_y >= 0:
            self.progress_callback(0.0, last_x, last_y)

    reset = cancel
