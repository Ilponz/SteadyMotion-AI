"""
Filtro Anti-Sobbalzo Meccanico per Carrozzine Elettroniche (Wheelchair Seismic Jolt Absorber 2D).
Progettato per SteadyMotion AI v3.0 / v3.1.

Obiettivo Clinico:
Nei pazienti con lesione midollare, distrofia muscolare o SLA montati su carrozzina elettronica,
il superamento di dossi, soglie di ascensori, guide delle porte, marciapiedi o dislivelli del pavimento
trasmette una violenta accelerazione istantanea (jolt / sobbalzo) all'asta di supporto
della webcam o al vassoio del laptop.

Dinamica Fisiologica vs Meccanica:
- Il movimento cefalico fisiologico ha un'accelerazione vettoriale raramente superiore a 3.0 norm/s²;
- L'urto meccanico della ruota contro un ostacolo (verticale o torsione laterale) genera un picco ad alta frequenza
  con accelerazione vettoriale ||a|| > 6.0 norm/s² (oltre 1200 px/s²) concentrato in 10-30 ms.

Principio di Funzionamento:
1. Calcola derivata prima (velocità vx, vy) e seconda (accelerazione ax, ay) della traiettoria 2D normalizzata.
2. Inizializzazione della velocità differenziale per evitare falsi allarmi al primo frame di movimento.
3. Rileva il transitorio di urto meccanico multidirezionale (||a|| > soglia jolt o |ax| > soglia o |ay| > soglia).
4. Entra in stato di "Shock Absorption": congela/smorza l'escursione bidimensionale per 150-180 ms,
   assorbendo l'energia dell'urto senza far schizzare il cursore a bordo schermo o innescare falsi scroll o clic distruttivi.
5. Rilascia dolcemente la posizione con filtro di ritorno esponenziale continuo C^1.
"""

import math
from typing import Optional, Tuple


class WheelchairJoltFilter:
    """Filtro dinamico vettoriale 2D di assorbimento urti e sobbalzi da movimento in carrozzina."""

    def __init__(
        self,
        jolt_accel_threshold: float = 6.0,
        lockout_duration_sec: float = 0.18,
        is_enabled: bool = True,
    ):
        self.jolt_accel_threshold = float(jolt_accel_threshold)
        self.lockout_duration_sec = float(lockout_duration_sec)
        self.is_enabled = bool(is_enabled)

        # Stato temporale e cinematico 2D
        self._last_x: float = 0.5
        self._last_y: float = 0.5
        self._last_vx: float = 0.0
        self._last_vy: float = 0.0
        self._has_velocity: bool = False
        self._last_t: float = 0.0

        # Stato assorbitore di shock
        self._is_shock_absorbing: bool = False
        self._shock_start_t: float = 0.0
        self._frozen_x: float = 0.5
        self._frozen_y: float = 0.5
        self._jolts_absorbed_count: int = 0
        self._lateral_jolts_count: int = 0

    @property
    def jolts_absorbed(self) -> int:
        return self._jolts_absorbed_count

    @property
    def lateral_jolts(self) -> int:
        return self._lateral_jolts_count

    def reset(self, initial_x: float = 0.5, initial_y: float = 0.5):
        """Reimposta lo stato interno del filtro."""
        self._last_x = float(initial_x)
        self._last_y = float(initial_y)
        self._last_vx = 0.0
        self._last_vy = 0.0
        self._has_velocity = False
        self._last_t = 0.0
        self._is_shock_absorbing = False
        self._shock_start_t = 0.0
        self._frozen_x = float(initial_x)
        self._frozen_y = float(initial_y)

    def filter_2d(self, raw_x: float, raw_y: float, now: float) -> Tuple[float, float, bool]:
        """
        Elabora il vettore 2D (raw_x, raw_y) normalizzato [0.0, 1.0].
        Rileva sobbalzi meccanici sia verticali (dossi) che laterali (urti carrozzina).
        Restituisce (filtered_x: float, filtered_y: float, is_jolt_active: bool).
        """
        if not self.is_enabled:
            return raw_x, raw_y, False

        if self._last_t <= 0.0:
            self._last_t = now
            self._last_x = raw_x
            self._last_y = raw_y
            self._frozen_x = raw_x
            self._frozen_y = raw_y
            self._has_velocity = False
            return raw_x, raw_y, False

        dt = now - self._last_t
        self._last_t = now
        if dt <= 1e-5 or dt > 0.25:
            self._last_x = raw_x
            self._last_y = raw_y
            self._has_velocity = False
            return raw_x, raw_y, False

        # Calcolo velocità istantanea
        instant_vx = (raw_x - self._last_x) / dt
        instant_vy = (raw_y - self._last_y) / dt

        # Primo frame con velocità calcolata: inizializza il registro di riferimento per la derivata seconda
        if not self._has_velocity:
            self._last_vx = instant_vx
            self._last_vy = instant_vy
            self._last_x = raw_x
            self._last_y = raw_y
            self._has_velocity = True
            return raw_x, raw_y, False

        instant_ax = abs(instant_vx - self._last_vx) / dt
        instant_ay = abs(instant_vy - self._last_vy) / dt
        self._last_vx = instant_vx
        self._last_vy = instant_vy

        # Magnitudo dell'accelerazione vettoriale d'urto
        vector_accel = math.hypot(instant_ax, instant_ay)

        # Innesco shock absorption su sobbalzo verticale O urto laterale
        if (vector_accel >= self.jolt_accel_threshold or
                instant_ax >= self.jolt_accel_threshold or
                instant_ay >= self.jolt_accel_threshold) and not self._is_shock_absorbing:
            self._is_shock_absorbing = True
            self._shock_start_t = now
            self._frozen_x = self._last_x
            self._frozen_y = self._last_y
            self._jolts_absorbed_count += 1
            if instant_ax >= self.jolt_accel_threshold:
                self._lateral_jolts_count += 1

        # Gestione periodo di smorzamento attivo
        if self._is_shock_absorbing:
            elapsed = now - self._shock_start_t
            if elapsed < self.lockout_duration_sec:
                # Trattiene il valore precedente ammortizzando la vibrazione ad alta frequenza
                alpha = elapsed / self.lockout_duration_sec
                damped_x = (1.0 - alpha) * self._frozen_x + alpha * raw_x
                damped_y = (1.0 - alpha) * self._frozen_y + alpha * raw_y
                self._last_x = damped_x
                self._last_y = damped_y
                return damped_x, damped_y, True
            else:
                self._is_shock_absorbing = False

        self._last_x = raw_x
        self._last_y = raw_y
        return raw_x, raw_y, False

    def filter_y(self, raw_y: float, now: float) -> Tuple[float, bool]:
        """Wrapper 1D per retro-compatibilità completa."""
        _, damped_y, is_jolt = self.filter_2d(self._last_x, raw_y, now)
        return damped_y, is_jolt
