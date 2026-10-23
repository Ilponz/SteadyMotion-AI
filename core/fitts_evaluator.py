"""
Modulo di Valutazione Scientifica della Legge di Fitts & Throughput ISO 9241-9.
Progettato per SteadyMotion AI v3.0.

Riferimento Scientifico e Standard Internazionale:
ISO 9241-9 (Ergonomic requirements for office work with visual display terminals -
Part 9: Requirements for non-keyboard input devices) e Fitts, P. M. (1954).

Metriche Calcolate:
1. Movement Time (MT, secondi): tempo intercorso tra l'inizio del puntamento e l'avvenuto clic.
2. Distance (D, pixel): distanza euclidea tra il punto di partenza e il centro del target.
3. Target Width (W, pixel): ampiezza/diametro del bersaglio interattivo.
4. Index of Difficulty (ID, bit):
      ID = log2(D / W + 1.0)
5. Throughput (TP, bit/secondo):
      TP = ID / MT
   Rappresenta la capacità di canale motorio informativo del paziente.
6. Error Rate (ER %): percentuale di clic fuori bersaglio o dwell abortiti durante il tragitto.
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
    ):
        self.target_id = target_id
        self.start_x = start_x
        self.start_y = start_y
        self.target_x = target_x
        self.target_y = target_y
        self.target_width = max(1.0, float(target_width))
        self.movement_time_sec = max(0.001, float(movement_time_sec))
        self.is_hit = is_hit

        # Distanza euclidea D
        dx = target_x - start_x
        dy = target_y - start_y
        self.distance = math.hypot(dx, dy)

        # Indice di Difficoltà ID (Shannon formulation)
        self.index_of_difficulty = math.log2((self.distance / self.target_width) + 1.0)

        # Throughput TP (bit/s)
        self.throughput = self.index_of_difficulty / self.movement_time_sec if self.is_hit else 0.0


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
    ) -> Optional[FittsTrialResult]:
        """Registra il completamento di un bersaglio calcolando ID, MT e TP."""
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
                "mean_index_of_difficulty": 0.0,
                "mean_throughput_bps": 0.0,
            }

        hits = [t for t in self.trials if t.is_hit]
        misses = [t for t in self.trials if not t.is_hit]

        mean_mt = sum(t.movement_time_sec for t in hits) / len(hits) if hits else 0.0
        mean_id = sum(t.index_of_difficulty for t in hits) / len(hits) if hits else 0.0
        mean_tp = sum(t.throughput for t in hits) / len(hits) if hits else 0.0
        error_rate = (len(misses) / len(self.trials)) * 100.0

        return {
            "total_trials": len(self.trials),
            "trials_completed": len(self.trials),
            "hits": len(hits),
            "misses": len(misses),
            "error_rate_pct": round(error_rate, 1),
            "mean_movement_time_sec": round(mean_mt, 3),
            "mean_index_of_difficulty": round(mean_id, 2),
            "mean_throughput_bps": round(mean_tp, 2),
        }

    def reset(self):
        """Azzera i dati della sessione di prova."""
        self.trials.clear()
        self._current_trial_start_time = None
        self._current_start_pos = None
