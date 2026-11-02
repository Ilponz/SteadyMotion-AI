"""
Modulo di Sicurezza Dwell su Azioni di Sistema Distruttive (Adaptive Dwell Safety Guard).
Progettato per SteadyMotion AI v3.0.

Obiettivo Clinico:
Risolvere il problema del "Midas Touch" involontario sulle aree critiche del sistema operativo.
Nei pazienti con patologie neuromuscolari (SLA, tetraplegia, corea, distonia),
lo sguardo o il capo possono indugiare involontariamente sull'angolo superiore destro
(pulsante di chiusura finestra 'X' di Windows) o sull'area della tray di sistema.
Un clic involontario provoca la chiusura immediata di software di scrittura, cartelle cliniche
o browser senza salvataggio, causando frustrazione e perdita del lavoro svolto.

Meccanismo di Protezione:
1. Rileva se il cursore (x, y) si trova all'interno di una "Zona a Rischio Elevato" (Danger Zone).
2. Estende dinamicamente il tempo di sosta (Dwell Time) applicando un fattore di sicurezza (1.75x di default).
3. Richiede una sosta intenzionale prolungata e cosciente per attivare l'azione.
4. Fornisce feedback sullo stato di protezione per informare l'HUD o il logger clinico.
"""

from typing import List, Optional, Tuple


class DwellSafetyGuard:
    """Controllore di sicurezza adattivo per prevenire clic distruttivi involontari."""

    def __init__(
        self,
        is_enabled: bool = True,
        safety_multiplier: float = 1.75,
        vx: int = 0,
        vy: int = 0,
        vw: int = 1920,
        vh: int = 1080,
    ):
        self.is_enabled = bool(is_enabled)
        self.safety_multiplier = max(1.10, min(3.50, float(safety_multiplier)))
        self.vx = int(vx)
        self.vy = int(vy)
        self.vw = int(vw)
        self.vh = int(vh)

        self._custom_danger_rects: List[Tuple[int, int, int, int]] = []
        self._system_danger_rects: List[Tuple[int, int, int, int]] = []
        self.update_screen_geometry(self.vx, self.vy, self.vw, self.vh)

    def update_screen_geometry(self, vx: int, vy: int, vw: int, vh: int):
        """Aggiorna la geometria dello schermo e ricalcola le zone di rischio predefinite."""
        self.vx = int(vx)
        self.vy = int(vy)
        self.vw = int(vw)
        self.vh = int(vh)

        self._system_danger_rects.clear()

        # Zona 1: Angolo Superiore Destro (Pulsante Chiudi Finestra / 'X' di Windows)
        # Larghezza standard pulsante chiusura: ~48-52 px, altezza ~36-40 px
        top_right_x1 = self.vx + self.vw - 52
        top_right_y1 = self.vy
        top_right_x2 = self.vx + self.vw
        top_right_y2 = self.vy + 42
        self._system_danger_rects.append((top_right_x1, top_right_y1, top_right_x2, top_right_y2))

    def add_custom_danger_zone(self, x1: int, y1: int, x2: int, y2: int):
        """Aggiunge una zona di rischio personalizzata (es. pulsante Elimina, Arresta Sistema)."""
        rx1, rx2 = min(x1, x2), max(x1, x2)
        ry1, ry2 = min(y1, y2), max(y1, y2)
        self._custom_danger_rects.append((rx1, ry1, rx2, ry2))

    def clear_custom_danger_zones(self):
        """Rimuove tutte le zone di rischio personalizzate."""
        self._custom_danger_rects.clear()

    def is_in_danger_zone(self, x: int, y: int) -> bool:
        """Verifica istantanea O(N) se il punto (x, y) ricade in una zona a rischio."""
        if not self.is_enabled:
            return False

        # Verifica zone di sistema predefinite
        for x1, y1, x2, y2 in self._system_danger_rects:
            if x1 <= x <= x2 and y1 <= y <= y2:
                return True

        # Verifica zone personalizzate
        for x1, y1, x2, y2 in self._custom_danger_rects:
            if x1 <= x <= x2 and y1 <= y <= y2:
                return True

        return False

    def evaluate_dwell_time(self, x: int, y: int, base_dwell_time: float) -> Tuple[bool, float]:
        """
        Calcola il tempo di dwell effettivo per la posizione corrente.
        Restituisce una tupla (is_danger: bool, effective_dwell_time: float).
        """
        if not self.is_enabled:
            return False, base_dwell_time

        in_danger = self.is_in_danger_zone(x, y)
        if in_danger:
            return True, base_dwell_time * self.safety_multiplier

        return False, base_dwell_time
