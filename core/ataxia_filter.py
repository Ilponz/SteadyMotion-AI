"""
Filtro Smorzatore Dinamico per Atassia Cerebellare e Tremore Intenzionale Terminale (2.5 - 4.5 Hz).
Progettato per SteadyMotion AI v3.0 / v3.1.

Inquadramento Clinico & Biomeccanico:
- Nei pazienti affetti da atassia cerebellare (ad es. atassia di Friedreich, atassie spino-cerebellari SCA,
  lesioni cerebellari post-traumatiche o ictus), il tremore si manifesta in modo 'intenzionale' o cinetico terminale:
  è minimo durante la traiettoria balistica rapida, ma esplode violentemente (frequenza 2.5 - 4.5 Hz)
  nella fase di decelerazione e arrivo sul target (dismetria e ipermetria con oscillazioni di overshooting).
- I filtri passa-basso standard a cutoff costante falliscono: se tarati troppo rigidi creano latenza inaccettabile;
  se tarati fluidi lasciano passare l'oscillazione a 3 Hz impedendo al puntatore di stazionare nel raggio di Dwell.

Principio di Funzionamento a Zero Heap Churn:
1. Analisi dei passaggi per lo zero della velocità (Zero-Crossing Directional Reversals):
   Monitora in tempo reale le inversioni di segno del vettore velocità (vx, vy) su una finestra circolare
   fissa di 450 ms senza riallocazioni in memoria.
2. Calcolo dello Spostamento Netto vs Velocità Istantanea (Net Speed Criterion):
   Distingue il tremore (alta velocità istantanea ma baricentro confinato, net_speed < 320 px/s)
   dalle traiettorie balistiche intenzionali (net_speed elevata senza inversioni).
3. Smorzamento Centroide Adattivo (Barycentric Damping):
   Il filtro ancora il puntatore verso il baricentro dell'inviluppo oscillatorio con fattore lambda in [0.40, 0.80],
   sopprimendo l'ampiezza dell'oscillazione del 50-70% e permettendo al Dwell di completarsi stabilmente.
4. Sblocco Balistico Istantaneo (Zero-Lag Exit):
   Non appena il paziente distoglie lo sguardo per muoversi verso un'altra area dello schermo (spostamento
   netto rapido > 350 px/s), lo smorzamento si disattiva istantaneamente.
"""

import math
from typing import Optional, Tuple


class AtaxiaIntentionDamper:
    """Smorzatore dinamico isotropo per tremore intenzionale da atassia cerebellare."""

    def __init__(
        self,
        window_duration_sec: float = 0.45,
        speed_threshold_px: float = 350.0,
        min_reversals_count: int = 2,
        max_damping_factor: float = 0.80,
        is_enabled: bool = True,
    ):
        self.window_duration_sec = float(window_duration_sec)
        self.speed_threshold_px = float(speed_threshold_px)
        self.min_reversals_count = int(min_reversals_count)
        self.max_damping_factor = float(max_damping_factor)
        self.is_enabled = bool(is_enabled)

        # Buffer circolare pre-allocato per velocità e posizioni (Zero Heap Allocations)
        self._capacity = 64
        self._t = [0.0] * self._capacity
        self._x = [0.0] * self._capacity
        self._y = [0.0] * self._capacity
        self._vx = [0.0] * self._capacity
        self._vy = [0.0] * self._capacity
        self._head: int = 0
        self._count: int = 0

        # Stato filtro
        self._last_t: float = 0.0
        self._last_x: float = 0.0
        self._last_y: float = 0.0
        self._last_vx: float = 0.0
        self._last_vy: float = 0.0

        # Metriche live
        self._tremor_score: float = 0.0
        self._measured_freq_hz: float = 0.0
        self._is_active: bool = False
        self._damped_x: float = 0.0
        self._damped_y: float = 0.0

    @property
    def is_tremor_active(self) -> bool:
        return self._is_active

    @property
    def tremor_score(self) -> float:
        return self._tremor_score

    @property
    def measured_frequency_hz(self) -> float:
        return self._measured_freq_hz

    def reset(self):
        """Azzera la memoria temporale e lo stato del filtro."""
        self._head = 0
        self._count = 0
        self._last_t = 0.0
        self._last_x = 0.0
        self._last_y = 0.0
        self._last_vx = 0.0
        self._last_vy = 0.0
        self._tremor_score = 0.0
        self._measured_freq_hz = 0.0
        self._is_active = False

    def process(self, x: float, y: float, now: float) -> Tuple[float, float, float]:
        """
        Elabora le coordinate (x, y) in pixel al tempo now (sec).
        Restituisce: (out_x: float, out_y: float, tremor_score: float [0.0, 1.0]).
        """
        if not self.is_enabled:
            return x, y, 0.0

        if self._last_t <= 0.0:
            self._last_t = now
            self._last_x = x
            self._last_y = y
            self._damped_x = x
            self._damped_y = y
            return x, y, 0.0

        dt = now - self._last_t
        if dt <= 1e-5:
            return self._damped_x, self._damped_y, self._tremor_score

        self._last_t = now

        # Derivata prima (velocità istantanea in px/s)
        vx = (x - self._last_x) / dt
        vy = (y - self._last_y) / dt
        self._last_x = x
        self._last_y = y

        # Inserimento nel ring buffer
        idx = self._head
        self._t[idx] = now
        self._x[idx] = x
        self._y[idx] = y
        self._vx[idx] = vx
        self._vy[idx] = vy
        self._head = (self._head + 1) % self._capacity
        if self._count < self._capacity:
            self._count += 1

        # Analisi finestra temporale retrograda
        cutoff_time = now - self.window_duration_sec
        reversals_x = 0
        reversals_y = 0
        sum_x = 0.0
        sum_y = 0.0
        valid_samples = 0

        prev_vx = None
        prev_vy = None

        for i in range(self._count):
            slot = (self._head - 1 - i + self._capacity) % self._capacity
            t_s = self._t[slot]
            if t_s < cutoff_time:
                break

            cur_vx = self._vx[slot]
            cur_vy = self._vy[slot]
            sum_x += self._x[slot]
            sum_y += self._y[slot]
            valid_samples += 1

            if prev_vx is not None:
                if (cur_vx * prev_vx < 0.0) and (abs(cur_vx) > 15.0 or abs(prev_vx) > 15.0):
                    reversals_x += 1
                if (cur_vy * prev_vy < 0.0) and (abs(cur_vy) > 15.0 or abs(prev_vy) > 15.0):
                    reversals_y += 1

            prev_vx = cur_vx
            prev_vy = cur_vy

        total_reversals = reversals_x + reversals_y

        # Spostamento netto (net speed)
        oldest_slot = (self._head - valid_samples + self._capacity) % self._capacity
        actual_window = now - self._t[oldest_slot]
        if actual_window > 0.08:
            net_dx = x - self._x[oldest_slot]
            net_dy = y - self._y[oldest_slot]
            net_speed = math.hypot(net_dx, net_dy) / actual_window
        else:
            net_speed = math.hypot(vx, vy)

        # Frequenza stimata per asse attivo
        active_axes = (1 if reversals_x > 0 else 0) + (1 if reversals_y > 0 else 0)
        if active_axes > 0 and actual_window > 0.08:
            estimated_cycles = (reversals_x + reversals_y) / (2.0 * active_axes)
            freq = estimated_cycles / actual_window
            self._measured_freq_hz = freq
        else:
            freq = 0.0

        # Criterio di attivazione: movimento confinato nello spazio con inversioni periodiche (1.8 - 6.5 Hz)
        if valid_samples >= 4 and net_speed < self.speed_threshold_px:
            if total_reversals >= self.min_reversals_count and 1.8 <= freq <= 6.5:
                intensity = min(1.0, 0.40 + 0.60 * (total_reversals / 3.0))
                self._tremor_score = intensity
                self._is_active = True
            else:
                self._tremor_score = max(0.0, self._tremor_score - 0.20)
                if self._tremor_score < 0.05:
                    self._is_active = False
        else:
            # Uscita balistica rapida: disattivazione istantanea
            self._tremor_score = 0.0
            self._is_active = False
            self._measured_freq_hz = 0.0

        # Applicazione Smorzamento Baricentrico
        if self._is_active and valid_samples > 0 and self._tremor_score > 0.10:
            centroid_x = sum_x / valid_samples
            centroid_y = sum_y / valid_samples
            lambda_factor = min(self.max_damping_factor, 0.40 + 0.40 * self._tremor_score)
            out_x = (1.0 - lambda_factor) * x + lambda_factor * centroid_x
            out_y = (1.0 - lambda_factor) * y + lambda_factor * centroid_y
        else:
            out_x = x
            out_y = y

        self._damped_x = out_x
        self._damped_y = out_y
        return out_x, out_y, self._tremor_score
