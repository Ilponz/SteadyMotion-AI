"""
Modulo UI Automation & Accessibility Magnetic Target Snapping.
Progettato per SteadyMotion AI v3.0 / v3.1.

Obiettivo Clinico:
Ridurre l'indice di difficoltà di Fitts (Fitts's Law Target Acquisition) per utenti affetti da
patologie neurodegenerative (SLA, Parkinson severo, tetraparesi spastica).

Principio di Funzionamento:
1. Quando il cursore filtrato si avvicina al baricentro di un elemento interattivo (pulsante GUI,
   link, checkbox, icona della palette), il sistema esercita un'attrazione gravitazionale dolce
   verso il centro del target.
2. Questo stabilizza enormemente il cursore durante la fase di Dwell (clic a sosta), impedendo
   che micro-scatti involontari o tremori periferici facciano uscire il cursore dal pulsante.
3. Velocità di Fuga (Breakout Velocity): Se l'utente esegue un movimento volontario rapido
   (v > 280 px/s), la forza di attrazione cade istantaneamente a zero (alpha = 0.0), consentendo
   al cursore di scivolare via senza alcuna sensazione di "blocco" o "viscosità fastidiosa".
4. Continuità C^1: La transizione di attrazione decresce quadraticamente a zero alla periferia del raggio
   e si azzera esattamente al centro (d=0 -> correzione = 0.000000 px).
5. Zero Heap Churn: Le strutture native Win32 (POINT, RECT) sono preallocate staticamente in memoria C.
   Le interrogazioni a WindowFromPoint vengono memorizzate nella cache del rettangolo attivo per evitare
   chiamate kernel superflue a 60-120 Hz.
"""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import math
import time
from typing import Dict, List, Optional, Tuple

user32 = ctypes.windll.user32

# Definizione tipi Win32 x64 sicuri
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL


@dataclass
class MagneticTarget:
    """Rappresentazione di un bersaglio interattivo agganciabile."""
    id: int
    left: int
    top: int
    right: int
    bottom: int
    is_clickable: bool = True

    @property
    def center_x(self) -> float:
        return (self.left + self.right) / 2.0

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2.0

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def contains(self, x: float, y: float) -> bool:
        return self.left <= x <= self.right and self.top <= y <= self.bottom

    def distance_to_center(self, x: float, y: float) -> float:
        return math.hypot(x - self.center_x, y - self.center_y)


class MagneticSnapper:
    """
    Motore di attrazione magnetica gravitazionale deterministica con breakout ad alta velocità
    e compatibilità zero-churn per il Core Loop a 60-120 Hz.
    """

    def __init__(
        self,
        snap_radius: float = 36.0,
        gravity_factor: float = 0.65,
        escape_velocity: float = 280.0,
        is_enabled: bool = True,
    ):
        self.snap_radius = float(snap_radius)
        self.gravity_factor = max(0.0, min(1.0, float(gravity_factor)))
        self.escape_velocity = float(escape_velocity)
        self.is_enabled = bool(is_enabled)

        # Stato cinematico per calcolo velocità e breakout
        self._last_x: Optional[float] = None
        self._last_y: Optional[float] = None
        self._last_time: Optional[float] = None
        self._current_velocity: float = 0.0
        self._is_snapped: bool = False
        self._snapped_target_id: Optional[int] = None

        # Cache bersagli simulati / headless per test e palette interna
        self._mock_targets: Dict[int, MagneticTarget] = {}
        self._next_mock_id: int = 1

        # Strutture Win32 pre-allocate (Zero Heap Churn)
        self._pt = wintypes.POINT()
        self._rect = wintypes.RECT()
        self._rect_byref = ctypes.byref(self._rect)

        # Cache finestra Win32 attiva per evitare polling kernel 60 Hz continuo
        self._cached_hwnd: Optional[int] = None
        self._cached_rect: Optional[Tuple[int, int, int, int]] = None
        self._cached_center: Optional[Tuple[float, float]] = None

    def update_params(
        self,
        is_enabled: Optional[bool] = None,
        snap_radius: Optional[float] = None,
        gravity_factor: Optional[float] = None,
        escape_velocity: Optional[float] = None,
    ):
        """Aggiorna i parametri di snapping a runtime."""
        if is_enabled is not None:
            self.is_enabled = bool(is_enabled)
        if snap_radius is not None:
            self.snap_radius = max(10.0, float(snap_radius))
        if gravity_factor is not None:
            self.gravity_factor = max(0.0, min(1.0, float(gravity_factor)))
        if escape_velocity is not None:
            self.escape_velocity = max(50.0, float(escape_velocity))

    def reset(self):
        """Ripristina la storia cinematica e la cache."""
        self._last_x = None
        self._last_y = None
        self._last_time = None
        self._current_velocity = 0.0
        self._is_snapped = False
        self._snapped_target_id = None
        self._cached_hwnd = None
        self._cached_rect = None
        self._cached_center = None

    def add_mock_target(self, left: int, top: int, right: int, bottom: int, is_clickable: bool = True) -> int:
        """Registra un bersaglio mock per test headless o componenti grafici interni."""
        tid = self._next_mock_id
        self._next_mock_id += 1
        self._mock_targets[tid] = MagneticTarget(tid, left, top, right, bottom, is_clickable)
        return tid

    def remove_mock_target(self, target_id: int):
        """Rimuove un bersaglio mock registrato."""
        self._mock_targets.pop(target_id, None)

    def clear_mock_targets(self):
        """Cancella tutti i bersagli mock registrati."""
        self._mock_targets.clear()

    @property
    def is_snapped(self) -> bool:
        """Indica se il cursore è attualmente attratto da un bersaglio."""
        return self._is_snapped

    @property
    def current_velocity(self) -> float:
        """Restituisce l'ultima velocità cinematica stimata del cursore (px/s)."""
        return self._current_velocity

    def _find_target_centroid(self, x: float, y: float) -> Optional[Tuple[float, float, Optional[int]]]:
        """
        Trova il centro del bersaglio più vicino entro il raggio di prossimità.
        Controlla prima i target mock (test / palette interna), poi interroga Win32.
        """
        # 1. Verifica bersagli mock registrati
        if self._mock_targets:
            best_target: Optional[MagneticTarget] = None
            min_dist = float("inf")

            for target in self._mock_targets.values():
                if not target.is_clickable:
                    continue
                dist = target.distance_to_center(x, y)
                if dist <= self.snap_radius and dist < min_dist:
                    min_dist = dist
                    best_target = target

            if best_target is not None:
                return best_target.center_x, best_target.center_y, best_target.id

        # 2. Verifica finestra Win32 tramite cache veloce
        if self._cached_rect is not None and self._cached_center is not None:
            c_left, c_top, c_right, c_bottom = self._cached_rect
            # Se siamo ancora nei pressi del rettangolo memorizzato in cache
            if (c_left - self.snap_radius <= x <= c_right + self.snap_radius and
                    c_top - self.snap_radius <= y <= c_bottom + self.snap_radius):
                cx, cy = self._cached_center
                dist = math.hypot(x - cx, y - cy)
                if dist <= self.snap_radius:
                    return cx, cy, None
            else:
                self._cached_hwnd = None
                self._cached_rect = None
                self._cached_center = None

        # 3. Interrogazione diretta Win32 WindowFromPoint
        try:
            self._pt.x = int(round(x))
            self._pt.y = int(round(y))
            hwnd = user32.WindowFromPoint(self._pt)
            if hwnd and user32.IsWindowVisible(hwnd):
                if user32.GetWindowRect(hwnd, self._rect_byref):
                    w = self._rect.right - self._rect.left
                    h = self._rect.bottom - self._rect.top
                    # Filtra solo elementi di dimensioni tipiche di controlli GUI (pulsanti, input, icone)
                    if 8 <= w <= 600 and 8 <= h <= 350:
                        cx = (self._rect.left + self._rect.right) / 2.0
                        cy = (self._rect.top + self._rect.bottom) / 2.0
                        self._cached_hwnd = hwnd
                        self._cached_rect = (self._rect.left, self._rect.top, self._rect.right, self._rect.bottom)
                        self._cached_center = (cx, cy)

                        dist = math.hypot(x - cx, y - cy)
                        if dist <= self.snap_radius:
                            return cx, cy, None
        except Exception:
            pass

        return None

    def apply_snap(self, x: float, y: float, now: float) -> Tuple[float, float]:
        """
        Applica l'attrazione gravitazionale verso il target più vicino.
        Se la velocità supera l'escape_velocity, l'attrazione decade istantaneamente a 0.
        """
        if not self.is_enabled:
            self._last_x = x
            self._last_y = y
            self._last_time = now
            self._is_snapped = False
            return x, y

        # Stima della velocità cinematica del cursore
        inst_v = 0.0
        if self._last_time is not None and self._last_x is not None and self._last_y is not None:
            dt = now - self._last_time
            if dt > 1e-6:
                dx = x - self._last_x
                dy = y - self._last_y
                inst_v = math.hypot(dx, dy) / dt
                self._current_velocity = 0.5 * self._current_velocity + 0.5 * inst_v
        else:
            self._current_velocity = 0.0

        self._last_x = x
        self._last_y = y
        self._last_time = now

        # Breakout: se il movimento è rapido e intenzionale, nessun aggancio (fuga immediata)
        if inst_v >= self.escape_velocity or self._current_velocity >= self.escape_velocity:
            self._is_snapped = False
            self._snapped_target_id = None
            return x, y

        # Ricerca del bersaglio più vicino
        target_info = self._find_target_centroid(x, y)
        if target_info is None:
            self._is_snapped = False
            self._snapped_target_id = None
            return x, y

        cx, cy, target_id = target_info
        d = math.hypot(x - cx, y - cy)

        if d > self.snap_radius or d < 1e-9:
            # d > R_snap: fuori portata; d == 0: già perfettamente al centro (correzione = 0)
            self._is_snapped = (d < 1e-9)
            self._snapped_target_id = target_id
            return x, y

        # Funzione di attrazione continua C^1: decadimento quadratico alla periferia
        # alpha = (1.0 - d / R)^2 * k_gravity
        ratio = 1.0 - (d / self.snap_radius)
        alpha = (ratio * ratio) * self.gravity_factor

        snapped_x = x + alpha * (cx - x)
        snapped_y = y + alpha * (cy - y)

        self._is_snapped = True
        self._snapped_target_id = target_id

        return snapped_x, snapped_y
