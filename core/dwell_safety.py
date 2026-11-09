"""
Modulo di Sicurezza Dwell su Azioni di Sistema Distruttive (Adaptive Dwell Safety Guard).
Progettato per SteadyMotion AI v3.0 / v3.1.

Obiettivo Clinico:
Risolvere il problema del "Midas Touch" involontario sulle aree critiche del sistema operativo.
Nei pazienti con patologie neuromuscolari (SLA, tetraplegia, corea, distonia),
lo sguardo o il capo possono indugiare involontariamente su:
1. Pulsanti di chiusura 'X' delle finestre (su qualsiasi monitor o finestra attiva non massimizzata);
2. Area del menu Start / Tray di sistema di Windows;
3. Pulsanti di distruzione dati / arresto sistema.

Meccanismo di Protezione:
1. Rileva se il cursore (x, y) si trova all'interno di una "Zona a Rischio Elevato" (Danger Zone):
   - Mappa le zone 'X' di chiusura per TUTTI i monitor attivi (Multi-Monitor Aware);
   - Sniffing dinamico Win32 GetForegroundWindow/GetWindowRect (a zero heap churn) per intercettare
     il pulsante di chiusura anche di finestre non massimizzate in centro schermo;
   - Angolo Menu Start e System Tray.
2. Estende dinamicamente il tempo di sosta (Dwell Time) applicando un fattore di sicurezza (1.75x - 2.5x).
3. Emette segnale di pericolo visivo per l'HUD (Shield Reticle e tonalità d'allerta).
4. Registra l'evento nella cartella clinica per tracciare le chiusure accidentali sventate.
"""

import ctypes
from ctypes import wintypes
import time
from typing import Any, List, Optional, Tuple

user32 = ctypes.windll.user32


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

        self.monitors: List[Any] = []
        self._custom_danger_rects: List[Tuple[int, int, int, int]] = []
        self._system_danger_rects: List[Tuple[int, int, int, int]] = []

        # Sniffing dinamico della finestra attiva (Foreground Window)
        self.protect_foreground_window: bool = True
        self._last_fg_check_t: float = 0.0
        self._cached_fg_danger_rect: Optional[Tuple[int, int, int, int]] = None
        self._rect_buf = wintypes.RECT()

        # Telemetria & Stato
        self.last_danger_type: str = ""
        self.is_last_danger: bool = False
        self.danger_dwell_events_count: int = 0

        self.update_screen_geometry(self.vx, self.vy, self.vw, self.vh)

    def update_screen_geometry(
        self,
        vx: int,
        vy: int,
        vw: int,
        vh: int,
        monitors: Optional[List[Any]] = None,
    ):
        """Aggiorna la geometria dello schermo e ricalcola le zone di rischio per tutti i monitor."""
        self.vx = int(vx)
        self.vy = int(vy)
        self.vw = int(vw)
        self.vh = int(vh)

        if monitors is not None:
            self.monitors = list(monitors)

        self._system_danger_rects.clear()

        # Se sono presenti monitor fisici censiti, protegge il bordo superiore destro di CIASCUN monitor
        if self.monitors:
            for m in self.monitors:
                # Pulsante di chiusura finestra massimizzata (X) per ciascun monitor
                # x in [m.right - 52, m.right], y in [m.top, m.top + 42]
                self._system_danger_rects.append((m.right - 52, m.top, m.right, m.top + 42))

                # Se monitor primario, protegge anche l'angolo Menu Start in basso a sinistra
                if getattr(m, "is_primary", False):
                    self._system_danger_rects.append((m.left, m.bottom - 48, m.left + 52, m.bottom))
        else:
            # Fallback coordinate desktop virtuale globale
            top_right_x1 = self.vx + self.vw - 52
            top_right_y1 = self.vy
            top_right_x2 = self.vx + self.vw
            top_right_y2 = self.vy + 42
            self._system_danger_rects.append((top_right_x1, top_right_y1, top_right_x2, top_right_y2))

    def _get_foreground_window_close_rect(self, now: float) -> Optional[Tuple[int, int, int, int]]:
        """
        Interroga la finestra attiva in primo piano (throttled a 100 ms a zero heap churn).
        Identifica la posizione esatta del pulsante 'X' della finestra anche se non massimizzata.
        """
        if not self.protect_foreground_window:
            return None

        if now - self._last_fg_check_t < 0.10:
            return self._cached_fg_danger_rect

        self._last_fg_check_t = now
        try:
            hwnd = user32.GetForegroundWindow()
            if hwnd == 0:
                self._cached_fg_danger_rect = None
                return None

            if user32.GetWindowRect(hwnd, ctypes.byref(self._rect_buf)):
                r = self._rect_buf
                # Considera solo finestre con dimensioni standard visibili
                if (r.right - r.left) > 120 and (r.bottom - r.top) > 80:
                    # Pulsante standard X in alto a destra della finestra attiva
                    # x1: r.right - 50, y1: r.top, x2: r.right, y2: r.top + 36
                    self._cached_fg_danger_rect = (r.right - 50, r.top, r.right, r.top + 36)
                    return self._cached_fg_danger_rect
        except Exception:
            pass

        self._cached_fg_danger_rect = None
        return None

    def add_custom_danger_zone(self, x1: int, y1: int, x2: int, y2: int):
        """Aggiunge una zona di rischio personalizzata (es. pulsante Elimina, Arresta Sistema)."""
        rx1, rx2 = min(x1, x2), max(x1, x2)
        ry1, ry2 = min(y1, y2), max(y1, y2)
        self._custom_danger_rects.append((rx1, ry1, rx2, ry2))

    def clear_custom_danger_zones(self):
        """Rimuove tutte le zone di rischio personalizzate."""
        self._custom_danger_rects.clear()

    def is_in_danger_zone(self, x: int, y: int, now: float = 0.0) -> bool:
        """Verifica istantanea O(N) se il punto (x, y) ricade in una zona a rischio."""
        if not self.is_enabled:
            self.is_last_danger = False
            self.last_danger_type = ""
            return False

        ix = int(x)
        iy = int(y)

        # 1. Verifica zone di sistema predefinite (pulsanti X dei monitor e Start Menu)
        for x1, y1, x2, y2 in self._system_danger_rects:
            if x1 <= ix <= x2 and y1 <= iy <= y2:
                self.is_last_danger = True
                self.last_danger_type = "system_close_or_start"
                return True

        # 2. Verifica zone personalizzate
        for x1, y1, x2, y2 in self._custom_danger_rects:
            if x1 <= ix <= x2 and y1 <= iy <= y2:
                self.is_last_danger = True
                self.last_danger_type = "custom_danger_rect"
                return True

        # 3. Verifica pulsante 'X' della finestra attiva in primo piano (non massimizzata)
        if self.protect_foreground_window:
            fg_rect = self._get_foreground_window_close_rect(now if now > 0.0 else time.perf_counter())
            if fg_rect is not None:
                fx1, fy1, fx2, fy2 = fg_rect
                if fx1 <= ix <= fx2 and fy1 <= iy <= fy2:
                    self.is_last_danger = True
                    self.last_danger_type = "foreground_window_close"
                    return True

        self.is_last_danger = False
        self.last_danger_type = ""
        return False

    def evaluate_dwell_time(
        self,
        x: int,
        y: int,
        base_dwell_time: float,
        now: float = 0.0,
    ) -> Tuple[bool, float]:
        """
        Calcola il tempo di dwell effettivo per la posizione corrente.
        Restituisce una tupla (is_danger: bool, effective_dwell_time: float).
        """
        if not self.is_enabled:
            return False, base_dwell_time

        in_danger = self.is_in_danger_zone(x, y, now=now)
        if in_danger:
            self.danger_dwell_events_count += 1
            return True, base_dwell_time * self.safety_multiplier

        return False, base_dwell_time
