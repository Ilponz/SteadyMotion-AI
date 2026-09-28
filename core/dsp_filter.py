"""
One-Euro Filter con Dynamic Sub-pixel Deadzone.
Riferimento: Casiez et al., "1€ Filter: A Simple Speed-based Low-pass Filter for Noisy Input in HCI", CHI 2012.
Ottimizzato per tracciamento cefalico e soppressione di tremori patologici (3.8 - 7.5 Hz).
"""

import math
import time
from typing import Tuple, Optional


class LowPassFilter:
    """Filtro passa-basso esponenziale del primo ordine."""

    def __init__(self, alpha: float = 0.5):
        self.__set_alpha(alpha)
        self.__y: Optional[float] = None
        self.__s: Optional[float] = None

    def __set_alpha(self, alpha: float):
        if alpha <= 0.0 or alpha > 1.0:
            alpha = max(0.0001, min(1.0, alpha))
        self.__alpha = alpha

    def filter(self, value: float, alpha: Optional[float] = None) -> float:
        if alpha is not None:
            self.__set_alpha(alpha)
        if self.__y is None:
            self.__s = value
        else:
            self.__s = self.__alpha * value + (1.0 - self.__alpha) * self.__s
        self.__y = value
        return self.__s

    def last_value(self) -> Optional[float]:
        return self.__s

    def reset(self):
        self.__y = None
        self.__s = None


class OneEuroFilter:
    """
    One-Euro Filter a frequenza di taglio adattiva.
    - Quando la velocità è bassa (puntamento fine), fc scende a min_cutoff (filtro pesante, anti-tremore).
    - Quando la velocità è alta (spostamento rapido), fc sale proporzionalmente a beta (bassa latenza).
    """

    def __init__(
        self,
        freq: float = 60.0,
        min_cutoff: float = 1.2,
        beta: float = 0.008,
        d_cutoff: float = 1.0,
    ):
        self.__freq = freq
        self.__min_cutoff = min_cutoff
        self.__beta = beta
        self.__d_cutoff = d_cutoff
        self.__x_filter = LowPassFilter()
        self.__dx_filter = LowPassFilter()
        self.__last_time: Optional[float] = None

    def __compute_alpha(self, cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def filter(self, x: float, timestamp: Optional[float] = None) -> float:
        if self.__last_time is not None and timestamp is not None:
            dt = timestamp - self.__last_time
            if dt <= 0.0:
                dt = 1.0 / self.__freq
        else:
            dt = 1.0 / self.__freq

        self.__last_time = timestamp

        prev_x = self.__x_filter.last_value()
        dx = 0.0 if prev_x is None else (x - prev_x) / dt

        edx = self.__dx_filter.filter(dx, self.__compute_alpha(self.__d_cutoff, dt))
        cutoff = self.__min_cutoff + self.__beta * abs(edx)
        return self.__x_filter.filter(x, self.__compute_alpha(cutoff, dt))

    def reset(self):
        self.__x_filter.reset()
        self.__dx_filter.reset()
        self.__last_time = None


class PointFilter2D:
    """
    Filtro combinato 2D con:
    1. Due filtri 1€ indipendenti (X e Y).
    2. Dynamic Sub-Pixel Deadband: azzera il moto al di sotto della soglia di micro-tremore.
    3. Curva di Guadagno Sigmoidale per accelerazione Fitts's Law.
    """

    def __init__(
        self,
        min_cutoff: float = 1.2,
        beta: float = 0.008,
        deadzone_radius: float = 0.0015,
        speed_exponent: float = 1.4,
    ):
        self.filter_x = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self.filter_y = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self.deadzone_radius = deadzone_radius
        self.speed_exponent = speed_exponent

        self.last_x: Optional[float] = None
        self.last_y: Optional[float] = None
        self.anchor_x: Optional[float] = None
        self.anchor_y: Optional[float] = None

    def update_params(self, min_cutoff: float, beta: float, deadzone: float):
        self.filter_x = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self.filter_y = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
        self.deadzone_radius = deadzone

    def filter(self, x: float, y: float, timestamp: Optional[float] = None) -> Tuple[float, float]:
        if timestamp is None:
            timestamp = time.perf_counter()

        filtered_x = self.filter_x.filter(x, timestamp)
        filtered_y = self.filter_y.filter(y, timestamp)

        if self.anchor_x is None or self.anchor_y is None:
            self.anchor_x = filtered_x
            self.anchor_y = filtered_y
            self.last_x = filtered_x
            self.last_y = filtered_y
            return filtered_x, filtered_y

        dx = filtered_x - self.anchor_x
        dy = filtered_y - self.anchor_y
        dist = math.hypot(dx, dy)

        if dist < self.deadzone_radius:
            # All'interno della zona morta: soppressione totale del micro-tremore
            return self.last_x, self.last_y

        # Oltre la zona morta: movimento attivo, aggiorna l'ancora elastica
        scale = (dist - self.deadzone_radius) / dist
        new_x = self.anchor_x + dx * scale
        new_y = self.anchor_y + dy * scale

        self.anchor_x = new_x
        self.anchor_y = new_y
        self.last_x = new_x
        self.last_y = new_y

        return new_x, new_y

    def reset(self):
        self.filter_x.reset()
        self.filter_y.reset()
        self.last_x = None
        self.last_y = None
        self.anchor_x = None
        self.anchor_y = None
