"""
Filtro Anti-Sobbalzo Meccanico per Carrozzine Elettroniche (Wheelchair Seismic Jolt Absorber).
Progettato per SteadyMotion AI v3.0 / v3.1.

Obiettivo Clinico:
Nei pazienti con lesione midollare, distrofia muscolare o SLA montati su carrozzina elettronica,
il superamento di dossi, soglie di ascensori, guide delle porte o dislivelli del pavimento
trasmette una forte accelerazione verticale istantanea (jolt / sobbalzo) all'asta di supporto
della webcam o al vassoio del laptop.

Dinamica Fisiologica vs Meccanica:
- Il movimento cefalico fisiologico ha un'accelerazione verticale raramente superiore a 3.0 norm/s²;
- L'urto meccanico della ruota contro un ostacolo genera un picco ad alta frequenza con
  accelerazione verticale > 6.0 norm/s² (oltre 1200 px/s²) concentrato in 10-30 ms.

Principio di Funzionamento:
1. Calcola derivata prima (velocità) e seconda (accelerazione) della traiettoria Y normalizzata.
2. Rileva il transitorio di urto meccanico (a_y > soglia jolt).
3. Entra in stato di "Shock Absorption": congela/smorza l'escursione verticale per 150-200 ms,
   assorbendo l'energia dell'urto senza far schizzare il cursore a bordo schermo o innescare falsi scroll.
4. Rilascia dolcemente la posizione con filtro di ritorno esponenziale continuo C^1.
"""

import math
from typing import Optional, Tuple


class WheelchairJoltFilter:
    """Filtro dinamico di assorbimento urti e sobbalzi da movimento in carrozzina."""

    def __init__(
        self,
        jolt_accel_threshold: float = 6.0,
        lockout_duration_sec: float = 0.18,
        is_enabled: bool = True,
    ):
        self.jolt_accel_threshold = float(jolt_accel_threshold)
        self.lockout_duration_sec = float(lockout_duration_sec)
        self.is_enabled = bool(is_enabled)

        # Stato temporale
        self._last_y: float = 0.5
        self._last_vy: float = 0.0
        self._last_t: float = 0.0

        # Stato assorbitore
        self._is_shock_absorbing: bool = False
        self._shock_start_t: float = 0.0
        self._frozen_y: float = 0.5
        self._jolts_absorbed_count: int = 0

    @property
    def jolts_absorbed(self) -> int:
        return self._jolts_absorbed_count

    def reset(self, initial_y: float = 0.5):
        """Reimposta lo stato interno del filtro."""
        self._last_y = float(initial_y)
        self._last_vy = 0.0
        self._last_t = 0.0
        self._is_shock_absorbing = False
        self._shock_start_t = 0.0
        self._frozen_y = float(initial_y)

    def filter_y(self, raw_y: float, now: float) -> Tuple[float, bool]:
        """
        Elabora la coordinata Y grezza [0.0, 1.0].
        Restituisce (filtered_y: float, is_jolt_active: bool).
        """
        if not self.is_enabled:
            return raw_y, False

        if self._last_t <= 0.0:
            self._last_t = now
            self._last_y = raw_y
            self._frozen_y = raw_y
            return raw_y, False

        dt = now - self._last_t
        self._last_t = now
        if dt <= 1e-5 or dt > 0.25:
            self._last_y = raw_y
            return raw_y, False

        # Calcolo velocità e accelerazione verticale istantanee
        instant_vy = (raw_y - self._last_y) / dt
        instant_ay = abs(instant_vy - self._last_vy) / dt
        self._last_vy = instant_vy

        # Verifica innesco urto da carrozzina
        if instant_ay >= self.jolt_accel_threshold and not self._is_shock_absorbing:
            self._is_shock_absorbing = True
            self._shock_start_t = now
            self._frozen_y = self._last_y
            self._jolts_absorbed_count += 1

        # Gestione periodo di smorzamento attivo
        if self._is_shock_absorbing:
            elapsed = now - self._shock_start_t
            if elapsed < self.lockout_duration_sec:
                # Trattiene il valore precedente ammortizzando la vibrazione
                alpha = elapsed / self.lockout_duration_sec
                # Rientro graduale ponderato
                damped_y = (1.0 - alpha) * self._frozen_y + alpha * raw_y
                self._last_y = damped_y
                return damped_y, True
            else:
                self._is_shock_absorbing = False

        self._last_y = raw_y
        return raw_y, False
