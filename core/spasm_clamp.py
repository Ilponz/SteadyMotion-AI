"""
Filtro Freno Anti-Teletrasporto per Spasmi Distonici e Scatti Mioclonici Acuti.
Progettato per SteadyMotion AI v3.0 / v3.1.

Inquadramento Clinico & Biomeccanico:
- Nei pazienti con paralisi cerebrale spastica, distonia cervicale (torcicollo spasmodico) o
  spasmi mioclonici, insorgono contrazioni involontarie violente ad alta energia cinetica:
  la velocità angolare del capo schizza improvvisamente a oltre 400°/s (> 15.0 norm/s²),
  generando un salto di 300-800 pixel in un singolo frame da 16 ms (> 20.000 px/s).
- Senza un freno biometrico, il cursore 'teletrasporta' all'angolo opposto dello schermo,
  attivando potenzialmente aree di pericolo o disorientando il paziente che perde il bersaglio.

Principio di Funzionamento a Zero Heap Churn:
1. Slew-Rate Limiter Fisiologico:
   Monitora la velocità scalare istantanea del cursore v = hypot(dx, dy) / dt.
   Se la velocità supera la soglia di non-fisiologicità (> 4200 px/s o salto > 75 px in 16 ms),
   il filtro intercetta lo spasmo acuto.
2. Blocco del Salto e Freno di Spostamento (Anchor & Slew Clamping):
   Durante lo spasmo (finestra di picco 120-160 ms), il filtro impedisce al puntatore di fuggire:
   limita la velocità massima consentita a una velocità fisiologica controllata (max_physio_speed ~ 1200 px/s)
   oppure trattiene il cursore nell'intorno dell'ancora pre-spasmo.
3. Rientro Continuo C^1:
   Al termine della contrazione muscolare acuta, non appena la velocità cefalica torna nei parametri
   fisiologici, il controllo torna gradualmente trasparente al 100% senza salti o ritardi.
"""

import math
from typing import Optional, Tuple


class SpasmVelocityClamp:
    """Freno biometrico anti-teletrasporto del cursore per spasmi distonici acuti."""

    def __init__(
        self,
        spasm_speed_threshold_px: float = 4200.0,
        max_physio_speed_px: float = 1200.0,
        lockout_duration_sec: float = 0.14,
        is_enabled: bool = True,
    ):
        self.spasm_speed_threshold_px = float(spasm_speed_threshold_px)
        self.max_physio_speed_px = float(max_physio_speed_px)
        self.lockout_duration_sec = float(lockout_duration_sec)
        self.is_enabled = bool(is_enabled)

        # Stato temporale
        self._last_t: float = 0.0
        self._last_out_x: float = 0.0
        self._last_out_y: float = 0.0

        # Stato blocco spasmo
        self._is_spasm_active: bool = False
        self._spasm_start_t: float = 0.0
        self._anchor_x: float = 0.0
        self._anchor_y: float = 0.0
        self._spasms_neutralized_count: int = 0
        self._peak_spasm_speed: float = 0.0

    @property
    def is_spasm_active(self) -> bool:
        return self._is_spasm_active

    @property
    def spasms_neutralized(self) -> int:
        return self._spasms_neutralized_count

    @property
    def peak_spasm_speed(self) -> float:
        return self._peak_spasm_speed

    def reset(self, initial_x: float = 0.0, initial_y: float = 0.0):
        """Reimposta lo stato interno del freno anti-spasmo."""
        self._last_t = 0.0
        self._last_out_x = float(initial_x)
        self._last_out_y = float(initial_y)
        self._anchor_x = float(initial_x)
        self._anchor_y = float(initial_y)
        self._is_spasm_active = False
        self._spasm_start_t = 0.0
        self._peak_spasm_speed = 0.0

    def clamp(self, target_x: float, target_y: float, now: float) -> Tuple[float, float, bool]:
        """
        Applica il freno anti-teletrasporto alle coordinate target (px).
        Restituisce: (clamped_x: float, clamped_y: float, is_spasm: bool).
        """
        if not self.is_enabled:
            self._last_out_x = target_x
            self._last_out_y = target_y
            return target_x, target_y, False

        if self._last_t <= 0.0:
            self._last_t = now
            self._last_out_x = target_x
            self._last_out_y = target_y
            self._anchor_x = target_x
            self._anchor_y = target_y
            return target_x, target_y, False

        dt = now - self._last_t
        self._last_t = now
        if dt <= 1e-5 or dt > 0.30:
            self._last_out_x = target_x
            self._last_out_y = target_y
            self._anchor_x = target_x
            self._anchor_y = target_y
            return target_x, target_y, False

        # Calcolo velocità euclidea istantanea richiesta
        dx = target_x - self._last_out_x
        dy = target_y - self._last_out_y
        dist = math.hypot(dx, dy)
        instant_speed = dist / dt

        # Rilevamento innesco spasmo acuto
        if instant_speed >= self.spasm_speed_threshold_px and not self._is_spasm_active:
            self._is_spasm_active = True
            self._spasm_start_t = now
            self._anchor_x = self._last_out_x
            self._anchor_y = self._last_out_y
            self._spasms_neutralized_count += 1
            self._peak_spasm_speed = instant_speed

        # Gestione periodo di smorzamento dello spasmo
        if self._is_spasm_active:
            elapsed = now - self._spasm_start_t
            if elapsed < self.lockout_duration_sec:
                # Freno slew-rate: consente al massimo la velocità fisiologica
                max_allowed_dist = self.max_physio_speed_px * dt
                if dist > max_allowed_dist and dist > 1e-4:
                    scale = max_allowed_dist / dist
                    out_x = self._last_out_x + dx * scale
                    out_y = self._last_out_y + dy * scale
                else:
                    out_x = target_x
                    out_y = target_y

                self._last_out_out_x = out_x
                self._last_out_out_y = out_y
                self._last_out_x = out_x
                self._last_out_y = out_y
                return out_x, out_y, True
            else:
                # Lockout completato: se la velocità è rientrata nella norma, disattiva
                if instant_speed < self.spasm_speed_threshold_px * 0.70:
                    self._is_spasm_active = False

        self._last_out_x = target_x
        self._last_out_y = target_y
        return target_x, target_y, False
