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

Proprietà Formali:
- Continuità C^1 in d = 0 (la derivata prima è continua, 0.000000 px di salto).
- Per gamma = 1.0: Funzione identità lineare classica (d * gain).
- Per gamma = 1.25 (default clinico): Abbattimento del 44% della sensibilità al 10% di escursione
  e mantenimento del 100% della corsa massima al bordo (m = 1.0).
- Monotonicità stretta: d_out(a) > d_out(b) per ogni a > b.
"""

import math
from typing import Tuple


class BallisticTransfer:
    """Funzione di trasferimento balistica non-lineare per il puntamento assistivo."""

    def __init__(self, gamma: float = 1.25, is_enabled: bool = True):
        self.gamma = max(1.0, min(2.5, float(gamma)))
        self.is_enabled = bool(is_enabled)

    def update_params(self, gamma: float, is_enabled: bool):
        self.gamma = max(1.0, min(2.5, float(gamma)))
        self.is_enabled = bool(is_enabled)

    def apply(self, d: float, gain: float) -> float:
        """
        Applica la curvatura balistica a un singolo asse di scostamento normalizzato d in [-0.5, 0.5].
        Restituisce lo scostamento amplificato e curvato.
        """
        if not self.is_enabled or self.gamma <= 1.001 or abs(d) < 1e-7:
            return d * gain

        sign = 1.0 if d >= 0.0 else -1.0
        abs_d = abs(d)

        # Magnitudo normalizzata nell'intervallo [0.0, 1.0] (dove 0.5 è il raggio massimo dello schermo)
        m = min(1.0, abs_d / 0.5)

        # Trasformazione polinomiale monotona
        m_curved = math.pow(m, self.gamma)

        # Riscalatura al dominio di output con guadagno specifico per quadrante
        return sign * (0.5 * m_curved) * gain

    def compute_normalized_xy(
        self,
        raw_x: float,
        raw_y: float,
        gx_left: float,
        gx_right: float,
        gy_up: float,
        gy_down: float,
    ) -> Tuple[float, float]:
        """
        Calcola le coordinate normalizzate [0.0, 1.0] applicando guadagni asimmetrici
        e curvatura balistica su entrambi gli assi.
        """
        dx = raw_x - 0.5
        dy = raw_y - 0.5

        gx = gx_left if dx < 0.0 else gx_right
        gy = gy_up if dy < 0.0 else gy_down

        out_dx = self.apply(dx, gx)
        out_dy = self.apply(dy, gy)

        norm_x = max(0.0, min(1.0, 0.5 + out_dx))
        norm_y = max(0.0, min(1.0, 0.5 + out_dy))

        return norm_x, norm_y
