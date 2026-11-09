"""
Modulo Controllore di Sospensione e Risveglio a Sguardo Autonomo (Gaze Sleep/Wake Controller).
Progettato per SteadyMotion AI v3.0.

Obiettivo Clinico:
Garantire al paziente tetraplegico o con SLA avanzata l'indipendenza totale nella gestione
dei momenti di pausa (es. guardare un film, leggere un libro, riposare gli occhi o conversare)
senza dover richiedere l'intervento del caregiver per premere F9 sulla tastiera fisica.

Meccanismo Funzionale:
1. Modalità ATTIVA:
   - Il paziente può sostare sul pulsante HUD "💤 Sleep" per disarmare istantaneamente il clic a sosta.
2. Modalità SLEEP (Dormiveglia):
   - Nessun clic viene iniettato su Windows (zero rischio di interferenza con video o lettura).
   - Il tracciamento della posa rimane attivo in background a bassissimo impatto.
   - Per RISVEGLIARE il puntamento, il paziente mantiene lo sguardo su una "Safe Wake Zone"
     (oppure esegue una sosta cosciente prolungata di 1.5-2.0s sulla tile di sblocco).
   - Un feedback sonoro progressivo conferma il risveglio avvenuto con successo.
"""

from typing import Callable, Optional, Tuple


class GazeSleepController:
    """Gestore dello stato di Standby e Risveglio autonomo a controllo cefalico/oculare."""

    def __init__(
        self,
        wake_dwell_time: float = 1.5,
        tolerance_radius: float = 35.0,
        on_sleep_callback: Optional[Callable[[], None]] = None,
        on_wake_callback: Optional[Callable[[], None]] = None,
    ):
        self.wake_dwell_time = max(0.5, float(wake_dwell_time))
        self.tolerance_radius = float(tolerance_radius)
        self.on_sleep_callback = on_sleep_callback
        self.on_wake_callback = on_wake_callback

        self.is_sleeping: bool = False
        self._wake_progress: float = 0.0
        self._anchor_x: float = 0.0
        self._anchor_y: float = 0.0
        self._last_t: float = 0.0

        # Coordinate della Wake-Up Target Zone a schermo (default: centro-alto dello schermo)
        self.wake_target_rect: Tuple[int, int, int, int] = (900, 10, 1020, 70)

    @property
    def wake_progress(self) -> float:
        return self._wake_progress

    @property
    def wake_target_center(self) -> Tuple[int, int]:
        x1, y1, x2, y2 = self.wake_target_rect
        return (int((x1 + x2) * 0.5), int((y1 + y2) * 0.5))

    def set_wake_dwell_time(self, seconds: float):
        self.wake_dwell_time = max(0.5, float(seconds))

    def reset_progress(self):
        self._wake_progress = 0.0
        self._last_t = 0.0

    def set_wake_target_rect(self, x1: int, y1: int, x2: int, y2: int):
        """Imposta l'area a schermo dedicata al risveglio."""
        self.wake_target_rect = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

    def trigger_sleep(self):
        """Mette immediatamente il sistema in stato di sleep autonomo."""
        self.is_sleeping = True
        self._wake_progress = 0.0
        self._last_t = 0.0
        if self.on_sleep_callback:
            try:
                self.on_sleep_callback()
            except Exception:
                pass

    def trigger_wake(self):
        """Risveglia immediatamente il sistema ripristinando il controllo."""
        self.is_sleeping = False
        self._wake_progress = 0.0
        self._last_t = 0.0
        if self.on_wake_callback:
            try:
                self.on_wake_callback()
            except Exception:
                pass

    def update_sleep_state(self, cursor_x: float, cursor_y: float, now: float) -> Tuple[bool, float]:
        """
        Aggiorna la macchina a stati di sonno/risveglio.
        Restituisce (is_sleeping: bool, wake_progress: float in [0.0, 1.0]).
        """
        if not self.is_sleeping:
            return False, 0.0

        if self._last_t <= 0.0:
            self._last_t = now
            self._anchor_x = cursor_x
            self._anchor_y = cursor_y
            return True, 0.0

        dt = now - self._last_t
        self._last_t = now

        if dt <= 0.0:
            return True, self._wake_progress

        effective_dt = min(0.20, dt)

        x1, y1, x2, y2 = self.wake_target_rect
        inside_target = (x1 <= cursor_x <= x2) and (y1 <= cursor_y <= y2)

        if inside_target:
            # Incremento progressivo sosta di risveglio cosciente
            self._wake_progress = min(1.0, self._wake_progress + (effective_dt / self.wake_dwell_time))
            if self._wake_progress >= 1.0:
                self.trigger_wake()
                return False, 1.0
        else:
            # Decadimento rapido se lo sguardo esce dal target di sblocco
            self._wake_progress = max(0.0, self._wake_progress - (effective_dt * 2.0))

        return True, self._wake_progress
