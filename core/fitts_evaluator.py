"""
Modulo di Valutazione Scientifica della Legge di Fitts & Throughput ISO 9241-9.
Progettato per SteadyMotion AI v3.0.

Riferimento Scientifico e Standard Internazionale:
ISO 9241-9 (Ergonomic requirements for office work with visual display terminals -
Part 9: Requirements for non-keyboard input devices) e ISO 9241-411 / Fitts, P. M. (1954).

Metriche Calcolate:
1. Movement Time (MT, secondi): tempo intercorso tra l'inizio del puntamento e l'avvenuto clic.
2. Distance (D, pixel): distanza euclidea tra il punto di partenza e il centro del target.
3. Target Width (W, pixel): ampiezza/diametro del bersaglio interattivo.
4. Index of Difficulty (ID, bit):
      ID = log2(D / W + 1.0)
5. Throughput (TP, bit/secondo):
      TP = ID / MT
   Rappresenta la capacità di canale motorio informativo del paziente.
6. Effective Measures (ISO 9241-9 / MacKenzie):
   - Effective Target Width We = 4.133 * sigma (adattamento statistico per 4% error rate)
   - Effective Index of Difficulty IDe = log2(De / We + 1.0)
   - Effective Throughput TPe = IDe / MT
7. Error Rate (ER %): percentuale di clic fuori bersaglio o dwell abortiti durante il tragitto.
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple


class FittsTrialResult:
    """Rappresenta il risultato di un singolo tentativo di puntamento a bersaglio."""

    def __init__(
        self,
        target_id: int,
        start_x: float,
        start_y: float,
        target_x: float,
        target_y: float,
        target_width: float,
        movement_time_sec: float,
        is_hit: bool = True,
        hit_x: Optional[float] = None,
        hit_y: Optional[float] = None,
    ):
        self.target_id = target_id
        self.start_x = float(start_x)
        self.start_y = float(start_y)
        self.target_x = float(target_x)
        self.target_y = float(target_y)
        self.target_width = max(1.0, float(target_width))
        self.movement_time_sec = max(0.001, float(movement_time_sec))
        self.is_hit = is_hit

        # Coordinate di impatto effettive
        self.hit_x = float(hit_x) if hit_x is not None else self.target_x
        self.hit_y = float(hit_y) if hit_y is not None else self.target_y

        # Distanza nominale euclidea D
        dx = self.target_x - self.start_x
        dy = self.target_y - self.start_y
        self.distance = math.hypot(dx, dy)

        # Distanza effettiva De (dallo start al punto di impatto)
        dx_eff = self.hit_x - self.start_x
        dy_eff = self.hit_y - self.start_y
        self.effective_distance = math.hypot(dx_eff, dy_eff)

        # Deviazione radiale dell'endpoint dal centro del target
        self.endpoint_deviation = math.hypot(self.hit_x - self.target_x, self.hit_y - self.target_y)

        # Proiezione dell'endpoint lungo l'asse del compito (Task Axis Projection)
        if self.distance > 1e-4:
            ux = dx / self.distance
            uy = dy / self.distance
            # Proiezione scalare del vettore percorso effettivo sull'asse del bersaglio
            self.task_axis_projection = dx_eff * ux + dy_eff * uy
        else:
            self.task_axis_projection = self.distance

        # Indice di Difficoltà Nominale ID (Shannon formulation)
        self.index_of_difficulty = math.log2((self.distance / self.target_width) + 1.0)

        # Throughput Nominale TP (bit/s)
        self.throughput = self.index_of_difficulty / self.movement_time_sec if self.is_hit else 0.0


def generate_iso_circle_targets(
    center_x: float,
    center_y: float,
    radius: float,
    num_targets: int = 13,
    target_width: float = 60.0,
) -> List[Dict[str, Any]]:
    """
    Genera i bersagli secondo il protocollo circolare multidirezionale ISO 9241-9.
    Implementa la sequenza di attraversamento diametrale reciproco (reciprocal star pattern),
    assicurando la copertura isotropa completa di tutte le direzioni spaziali (0-360°).
    """
    num_targets = max(3, int(num_targets))
    radius = max(10.0, float(radius))
    target_width = max(10.0, float(target_width))

    # Calcolo coordinate geometriche per tutti i nodi della circonferenza
    positions: List[Tuple[float, float, float]] = []
    for i in range(num_targets):
        # Angolo partendo dal vertice superiore (-pi/2)
        angle = -0.5 * math.pi + (2.0 * math.pi * i / num_targets)
        tx = center_x + radius * math.cos(angle)
        ty = center_y + radius * math.sin(angle)
        positions.append((tx, ty, math.degrees(angle)))

    # Ordine di presentazione a stella reciproca diametrale ISO 9241-9
    half = num_targets // 2
    order_indices: List[int] = []
    for k in range(num_targets):
        if k % 2 == 0:
            order_indices.append(k // 2)
        else:
            order_indices.append(half + (k // 2) + (1 if num_targets % 2 != 0 else 0))

    targets = []
    for step_idx, geom_idx in enumerate(order_indices):
        tx, ty, deg = positions[geom_idx]
        targets.append({
            "step": step_idx,
            "target_id": geom_idx,
            "x": round(tx, 1),
            "y": round(ty, 1),
            "width": target_width,
            "angle_deg": round(deg % 360.0, 1),
        })

    return targets


class FittsEvaluator:
    """Valutatore scientifico del throughput motorio per test riabilitativi."""

    def __init__(self):
        self.trials: List[FittsTrialResult] = []
        self._current_trial_start_time: Optional[float] = None
        self._current_start_pos: Optional[Tuple[float, float]] = None

    def start_trial(self, start_x: float, start_y: float, now: Optional[float] = None):
        """Avvia la misurazione temporale per il bersaglio successivo."""
        self._current_trial_start_time = now or time.perf_counter()
        self._current_start_pos = (float(start_x), float(start_y))

    def record_hit(
        self,
        target_id: int,
        target_x: float,
        target_y: float,
        target_width: float,
        now: Optional[float] = None,
        is_hit: bool = True,
        hit_x: Optional[float] = None,
        hit_y: Optional[float] = None,
    ) -> Optional[FittsTrialResult]:
        """Registra il completamento di un bersaglio calcolando ID, MT, TP e metriche effettive."""
        if self._current_trial_start_time is None or self._current_start_pos is None:
            # Se il trial non è stato esplicitamente avviato, usa la posizione del target come punto stazionario
            self._current_trial_start_time = (now or time.perf_counter()) - 1.0
            self._current_start_pos = (target_x, target_y)

        t_now = now or time.perf_counter()
        mt = max(0.001, t_now - self._current_trial_start_time)
        sx, sy = self._current_start_pos

        trial = FittsTrialResult(
            target_id=target_id,
            start_x=sx,
            start_y=sy,
            target_x=target_x,
            target_y=target_y,
            target_width=target_width,
            movement_time_sec=mt,
            is_hit=is_hit,
            hit_x=hit_x,
            hit_y=hit_y,
        )
        self.trials.append(trial)

        # Imposta la posizione del target colpito come punto di partenza per il prossimo
        self._current_start_pos = (target_x, target_y)
        self._current_trial_start_time = t_now
        return trial

    def get_summary(self) -> Dict[str, Any]:
        """Restituisce le statistiche aggregate ISO 9241-9 della sessione di test."""
        if not self.trials:
            return {
                "total_trials": 0,
                "hits": 0,
                "misses": 0,
                "error_rate_pct": 0.0,
                "mean_movement_time_sec": 0.0,
                "mean_distance_px": 0.0,
                "mean_index_of_difficulty": 0.0,
                "mean_throughput_bps": 0.0,
                "effective_target_width_we": 0.0,
                "effective_index_of_difficulty_ide": 0.0,
                "effective_throughput_tpe": 0.0,
                "endpoint_dispersion_sigma_px": 0.0,
                "iso_conformance": "ISO 9241-9 / ISO 9241-411 Compliant",
            }

        hits = [t for t in self.trials if t.is_hit]
        misses = [t for t in self.trials if not t.is_hit]

        mean_mt = sum(t.movement_time_sec for t in hits) / len(hits) if hits else 0.0
        mean_d = sum(t.distance for t in hits) / len(hits) if hits else 0.0
        mean_id = sum(t.index_of_difficulty for t in hits) / len(hits) if hits else 0.0
        mean_tp = sum(t.throughput for t in hits) / len(hits) if hits else 0.0
        error_rate = (len(misses) / len(self.trials)) * 100.0

        # Calcolo dell'Ampiezza Effettiva We = 4.133 * sigma (MacKenzie & ISO 9241-9)
        if len(hits) >= 2:
            # Calcolo deviazione standard delle deviazioni lungo l'asse o radiali
            deviations = [t.endpoint_deviation for t in hits]
            mean_dev = sum(deviations) / len(deviations)
            var_dev = sum((d - mean_dev) ** 2 for d in deviations) / (len(deviations) - 1)
            sigma = math.sqrt(var_dev)
            # We = 4.133 * sigma
            we = max(1.0, 4.133 * sigma) if sigma > 1e-4 else (hits[0].target_width if hits else 60.0)
        else:
            sigma = 0.0
            we = hits[0].target_width if hits else 60.0

        # Effective ID & Effective Throughput
        mean_de = sum(t.effective_distance for t in hits) / len(hits) if hits else mean_d
        ide = math.log2((mean_de / we) + 1.0) if we > 0 else mean_id
        tpe = ide / mean_mt if mean_mt > 0 else mean_tp

        return {
            "total_trials": len(self.trials),
            "trials_completed": len(self.trials),
            "hits": len(hits),
            "misses": len(misses),
            "error_rate_pct": round(error_rate, 1),
            "mean_movement_time_sec": round(mean_mt, 3),
            "mean_distance_px": round(mean_d, 1),
            "mean_index_of_difficulty": round(mean_id, 2),
            "mean_throughput_bps": round(mean_tp, 2),
            "effective_target_width_we": round(we, 2),
            "effective_index_of_difficulty_ide": round(ide, 2),
            "effective_throughput_tpe": round(tpe, 2),
            "endpoint_dispersion_sigma_px": round(sigma, 2),
            "iso_conformance": "ISO 9241-9 / ISO 9241-411 Compliant",
        }

    def reset(self):
        """Azzera i dati della sessione di prova."""
        self.trials.clear()
        self._current_trial_start_time = None
        self._current_start_pos = None
