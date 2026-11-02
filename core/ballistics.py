"""
Curva Balistica Fisiologica e Funzione di Trasferimento Non-Lineare (Fitts's Law Transfer Function).
Progettata per SteadyMotion AI v3.0.

Obiettivo Clinico:
Risolvere il trade-off fondamentale tra:
1. Micro-puntamento ad altissima precisione (checkbox 16x16 px, icone ravvicinate, link web)
   senza risentire del tremore o dell'ipersensibilità al centro;
2. Ampia reachability dello schermo intero (anche monitor multi-display o 4K)
   senza richiedere sforzi o iper-estensioni cervicali al paziente.

Modello Matematico:
Dato lo scostamento normalizzato rispetto al centro d in [-0.5, 0.5]:
  m = |d| / 0.5  (magnitudo normalizzata in [0.0, 1.0])
  m_curved = m ^ gamma
  d_out = sign(d) * 0.5 * m_curved * gain

Proprieta Formali:
- Continuita C^1 in d = 0 (la derivata prima e continua, 0.000000 px di salto).
- Per gamma = 1.0: Funzione identita lineare classica (d * gain).
- Per gamma = 1.25 (default clinico): Abbattimento del 44% della sensibilita al 10% di escursione
  e mantenimento del 100% della corsa massima al bordo (m = 1.0).
- Monotonicita stretta: d_out(a) > d_out(b) per ogni a > b.
"""

import math
from typing import Tuple


class BallisticTransfer:
    """Funzione di trasferimento balistica non-lineare per il puntamento assistivo."""

    def __init__(self, gamma: float = 1.25, is_enabled: bool = True, sniper_mode: bool = True):
        self.gamma = max(1.0, min(2.5, float(gamma)))
        self.is_enabled = bool(is_enabled)
        self.sniper_mode = bool(sniper_mode)
        self._last_raw_x: float = 0.5
        self._last_raw_y: float = 0.5
        self._last_t: float = 0.0
        self._velocity: float = 0.15

    def update_params(self, gamma: float, is_enabled: bool, sniper_mode: bool = True):
        self.gamma = max(1.0, min(2.5, float(gamma)))
        self.is_enabled = bool(is_enabled)
        self.sniper_mode = bool(sniper_mode)

    def compute_velocity_scale(self, raw_x: float, raw_y: float, now: float) -> float:
        """
        Calcola la modulazione di precisione dipendente dalla velocita (Sniper Deceleration).
        Quando l'utente rallenta per centrare un micro-bersaglio, la sensibilita scende fino al 40%
        per eliminare il tremore residuo e facilitare la sosta Dwell su aree ridotte (16x16 px).
        """
        if not self.sniper_mode or now <= self._last_t:
            return 1.0

        dt = now - self._last_t
        if dt > 0.20:
            self._last_raw_x = raw_x
            self._last_raw_y = raw_y
            self._last_t = now
            return 1.0

        dx = raw_x - self._last_raw_x
        dy = raw_y - self._last_raw_y
        dist = math.hypot(dx, dy)
        instant_v = dist / dt if dt > 1e-5 else 0.0

        self._velocity = 0.70 * self._velocity + 0.30 * instant_v
        self._last_raw_x = raw_x
        self._last_raw_y = raw_y
        self._last_t = now

        v_thresh = 0.10
        if self._velocity < v_thresh:
            scale = 0.40 + 0.60 * (self._velocity / v_thresh)
            return max(0.40, min(1.0, scale))

        return 1.0

    def apply(self, d: float, gain: float, v_scale: float = 1.0) -> float:
        """
        Applica la curvatura balistica e la modulazione di precisione a un singolo asse di scostamento normalizzato d in [-0.5, 0.5].
        Restituisce lo scostamento amplificato e curvato.
        """
        effective_gain = gain * v_scale
        if not self.is_enabled or self.gamma <= 1.001 or abs(d) < 1e-7:
            return d * effective_gain

        sign = 1.0 if d >= 0.0 else -1.0
        abs_d = abs(d)

        # Magnitudo normalizzata nell'intervallo [0.0, 1.0] (dove 0.5 e il raggio massimo dello schermo)
        m = min(1.0, abs_d / 0.5)

        # Trasformazione polinomiale monotona
        m_curved = math.pow(m, self.gamma)

        # Riscalatura al dominio di output con guadagno specifico per quadrante
        return sign * (0.5 * m_curved) * effective_gain

    def compute_normalized_xy(
        self,
        raw_x: float,
        raw_y: float,
        gx_left: float,
        gx_right: float,
        gy_up: float,
        gy_down: float,
        now: float = 0.0,
    ) -> Tuple[float, float]:
        """
        Calcola le coordinate normalizzate [0.0, 1.0] applicando guadagni asimmetrici,
        curvatura balistica e modulazione dinamica di precisione (Sniper Mode).
        """
        v_scale = 1.0
        if now > 0.0 and self.sniper_mode:
            v_scale = self.compute_velocity_scale(raw_x, raw_y, now)

        dx = raw_x - 0.5
        dy = raw_y - 0.5

        gx = gx_left if dx < 0.0 else gx_right
        gy = gy_up if dy < 0.0 else gy_down

        out_dx = self.apply(dx, gx, v_scale=v_scale)
        out_dy = self.apply(dy, gy, v_scale=v_scale)

        norm_x = max(0.0, min(1.0, 0.5 + out_dx))
        norm_y = max(0.0, min(1.0, 0.5 + out_dy))

        return norm_x, norm_y
