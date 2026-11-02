"""
Modulo UI Automation & Accessibility Magnetic Target Snapping.
Progettato per SteadyMotion AI v3.0 / v3.1.

Obiettivo Clinico:
Ridurre l'indice di difficoltà di Fitts (Fitts's Law Target Acquisition) per utenti affetti da
patologie neurodegenerative (SLA, Parkinson severo, tetraparesi spastica).

Principio di Funzionamento:
1. Quando il cursore filtrato si avvicina al baricentro di un elemento interattivo (pulsante GUI,
   link, checkbox, icona della palette, controlli web/Electron), il sistema esercita un'attrazione
   gravitazionale dolce verso il centro del target.
2. Questo stabilizza enormemente il cursore durante la fase di Dwell (clic a sosta), impedendo
   che micro-scatti involontari o tremori periferici facciano uscire il cursore dal pulsante.
3. Velocità di Fuga (Breakout Velocity): Se l'utente esegue un movimento volontario rapido
   (v > 280 px/s), la forza di attrazione cade istantaneamente a zero (alpha = 0.0), consentendo
   al cursore di scivolare via senza alcuna sensazione di "blocco" o "viscosità fastidiosa".
4. Continuità C^1: La transizione di attrazione decresce quadraticamente a zero alla periferia del raggio
   e si azzera esattamente al centro (d=0 -> correzione = 0.000000 px).
5. Zero Heap Churn & Decoupled UIA: Le strutture native Win32 (POINT, RECT) sono preallocate
   staticamente in memoria C. L'ispezione avanzata Microsoft UI Automation (COM IUIAutomation) opera
   su un thread worker asincrono in background per non bloccare mai il loop a 60-120 Hz della camera.
"""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import math
import threading
import time
from typing import Dict, List, Optional, Tuple

user32 = ctypes.windll.user32
ole32 = ctypes.oledll.ole32

# Definizione tipi Win32 x64 sicuri
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL


# ==============================================================================
# Definizione Strutture e Vtable COM per Microsoft UI Automation (ctypes nativo)
# ==============================================================================

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8)
    ]

    @classmethod
    def from_str(cls, s: str) -> "GUID":
        s = s.strip("{}")
        parts = s.split("-")
        d1 = int(parts[0], 16)
        d2 = int(parts[1], 16)
        d3 = int(parts[2], 16)
        d4_bytes = bytes.fromhex(parts[3] + parts[4])
        d4 = (ctypes.c_ubyte * 8)(*d4_bytes)
        return cls(d1, d2, d3, d4)


class POINT_VAL(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


# Prototipi funzioni COM
proto_ElementFromPoint = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, POINT_VAL, ctypes.POINTER(ctypes.c_void_p)
)
proto_GetBoundingRect = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(wintypes.RECT)
)
proto_GetControlType = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_void_p, ctypes.POINTER(ctypes.c_long)
)
proto_Release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)

# CLSID CUIAutomation: {FF48DBA4-60EF-4201-AA87-54103EEF594E}
# IID IUIAutomation:   {30CBE57D-D9D0-452A-AB13-7AC5AC4825EE}
CLSID_CUIAutomation = GUID.from_str("{FF48DBA4-60EF-4201-AA87-54103EEF594E}")
IID_IUIAutomation = GUID.from_str("{30CBE57D-D9D0-452A-AB13-7AC5AC4825EE}")

# UIA Control Types interattivi prioritari per lo snapping
INTERACTIVE_CONTROL_TYPES = {
    50000,  # Button
    50002,  # CheckBox
    50003,  # ComboBox
    50004,  # Edit
    50005,  # Hyperlink
    50006,  # Image
    50007,  # ListItem
    50011,  # MenuItem
    50013,  # RadioButton
    50015,  # Slider
    50019,  # TabItem
    50024,  # TreeItem
    50025,  # Custom
    50031,  # SplitButton
    50035,  # HeaderItem
}


# Costanti per il filtraggio dimensionale dei bersagli Win32 (Anti-Giant Container Trap)
# Prevengono l'attrazione spuria verso pannelli generici, canvas, finestre intere o WebViews.
MAX_SNAP_WIDTH = 480
MAX_SNAP_HEIGHT = 220
MAX_SNAP_AREA = 75000
MIN_SNAP_DIM = 8


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


class AsyncUIAutomationScanner:
    """
    Scanner asincrono in background per Microsoft UI Automation (COM STA).
    Ispeziona i controlli interni di Chrome, Edge, Firefox ed Electron senza mai bloccare
    il Core Loop di tracciamento a 60-120 Hz.
    """

    def __init__(
        self,
        max_w: int = MAX_SNAP_WIDTH,
        max_h: int = MAX_SNAP_HEIGHT,
        max_area: int = MAX_SNAP_AREA,
        min_dim: int = MIN_SNAP_DIM,
    ):
        self.max_w = max_w
        self.max_h = max_h
        self.max_area = max_area
        self.min_dim = min_dim

        self._req_x: int = 0
        self._req_y: int = 0
        self._has_request: bool = False
        self._last_req_time: float = 0.0
        self._running: bool = True

        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)

        self._latest_target: Optional[Tuple[int, int, int, int, float, float]] = None
        self._target_lock = threading.Lock()
        self.is_available: bool = False

        self._thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="UIAutomationScannerWorker",
        )
        self._thread.start()

    def request_inspection(self, x: float, y: float):
        """Richiede l'ispezione asincrona delle coordinate specificate (con throttling)."""
        now = time.perf_counter()
        # Throttling: massimo 1 richiesta ogni 35 ms per non saturare la coda COM
        if now - self._last_req_time < 0.035:
            return

        with self._cv:
            self._req_x = int(round(x))
            self._req_y = int(round(y))
            self._has_request = True
            self._last_req_time = now
            self._cv.notify()

    def get_target(self, x: float, y: float, snap_radius: float) -> Optional[Tuple[float, float]]:
        """
        Restituisce il baricentro dell'ultimo target UIA agganciato se il cursore è nelle vicinanze.
        Se il cursore si è allontanato, invalida automaticamente il target.
        """
        with self._target_lock:
            if self._latest_target is None:
                return None
            l, t, r, b, cx, cy = self._latest_target

            # Verifica se il cursore è ancora entro il raggio di influenza del target
            if (l - snap_radius <= x <= r + snap_radius and
                    t - snap_radius <= y <= b + snap_radius):
                return cx, cy

            # Se il cursore si è allontanato oltre 1.5x il raggio, resetta
            if not (l - snap_radius * 1.5 <= x <= r + snap_radius * 1.5 and
                    t - snap_radius * 1.5 <= y <= b + snap_radius * 1.5):
                self._latest_target = None
            return None

    def clear_target(self):
        """Cancella il target corrente in cache."""
        with self._target_lock:
            self._latest_target = None

    def _worker_loop(self):
        """Thread STA dedicato all'interrogazione COM di UI Automation."""
        try:
            ole32.CoInitialize(None)
            p_auto = ctypes.c_void_p()
            hr = ole32.CoCreateInstance(
                ctypes.byref(CLSID_CUIAutomation),
                None,
                1,  # CLSCTX_INPROC_SERVER
                ctypes.byref(IID_IUIAutomation),
                ctypes.byref(p_auto),
            )
            if hr != 0 or not p_auto.value:
                return

            vtable = ctypes.cast(p_auto, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
            fn_ElementFromPoint = proto_ElementFromPoint(vtable[7])
            fn_Release = proto_Release(vtable[2])
            self.is_available = True

            rect_out = wintypes.RECT()
            pt_in = POINT_VAL(0, 0)
            p_elem = ctypes.c_void_p()
            ctype_out = ctypes.c_long()

            while self._running:
                with self._cv:
                    while not self._has_request and self._running:
                        self._cv.wait(timeout=0.08)
                    if not self._running:
                        break
                    x = self._req_x
                    y = self._req_y
                    self._has_request = False

                pt_in.x = x
                pt_in.y = y
                p_elem.value = 0

                try:
                    hr_elem = fn_ElementFromPoint(p_auto, pt_in, ctypes.byref(p_elem))
                    if hr_elem == 0 and p_elem.value:
                        elem_vtable = ctypes.cast(p_elem, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
                        fn_GetRect = proto_GetBoundingRect(elem_vtable[43])
                        fn_GetType = proto_GetControlType(elem_vtable[21])
                        fn_RelElem = proto_Release(elem_vtable[2])

                        hr_rect = fn_GetRect(p_elem, ctypes.byref(rect_out))
                        hr_type = fn_GetType(p_elem, ctypes.byref(ctype_out))
                        fn_RelElem(p_elem)

                        if hr_rect == 0:
                            l, t, r, b = rect_out.left, rect_out.top, rect_out.right, rect_out.bottom
                            w = r - l
                            h = b - t
                            area = w * h

                            # Filtro Anti-Giant Container Trap
                            if (self.min_dim <= w <= self.max_w and
                                    self.min_dim <= h <= self.max_h and
                                    area <= self.max_area):
                                # Accetta controlli interattivi o elementi a dimensione pulsante
                                is_interactive = (ctype_out.value in INTERACTIVE_CONTROL_TYPES) or (w <= 240 and h <= 80)
                                if is_interactive:
                                    cx = (l + r) / 2.0
                                    cy = (t + b) / 2.0
                                    with self._target_lock:
                                        self._latest_target = (l, t, r, b, cx, cy)
                                    continue
                except Exception:
                    pass

                time.sleep(0.015)

            fn_Release(p_auto)
            ole32.CoUninitialize()
        except Exception:
            pass

    def stop(self):
        """Arresta in sicurezza il worker thread e rilascia l'apartment COM."""
        with self._cv:
            self._running = False
            self._cv.notify_all()
        if self._thread.is_alive():
            self._thread.join(timeout=0.4)


class MagneticSnapper:
    """
    Motore di attrazione magnetica gravitazionale deterministica con breakout ad alta velocità,
    ispezione asincrona UI Automation e compatibilità zero-churn per il Core Loop a 60-120 Hz.
    """

    def __init__(
        self,
        snap_radius: float = 36.0,
        gravity_factor: float = 0.65,
        escape_velocity: float = 280.0,
        is_enabled: bool = True,
        enable_uia: bool = True,
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

        # Scanner asincrono UI Automation per controlli profondi (Chrome/Edge/Electron)
        self._enable_uia = enable_uia
        self._uia_scanner: Optional[AsyncUIAutomationScanner] = (
            AsyncUIAutomationScanner() if enable_uia else None
        )

    def __del__(self):
        self.close()

    def close(self):
        """Arresta il worker thread UIA su spegnimento."""
        if self._uia_scanner is not None:
            self._uia_scanner.stop()
            self._uia_scanner = None

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
        if self._uia_scanner is not None:
            self._uia_scanner.clear_target()

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
        Priorità:
        1. Bersagli mock registrati (test headless, palette HUD interna).
        2. Cache finestra Win32 attiva.
        3. Cache asincrona Microsoft UI Automation (Chrome/Electron/Web).
        4. Interrogazione immediata Win32 WindowFromPoint.
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

        # 3. Verifica bersaglio da UI Automation asincrono (Chrome/Web/Electron)
        if self._uia_scanner is not None:
            uia_centroid = self._uia_scanner.get_target(x, y, self.snap_radius)
            if uia_centroid is not None:
                cx, cy = uia_centroid
                dist = math.hypot(x - cx, y - cy)
                if dist <= self.snap_radius:
                    return cx, cy, None

        # 4. Se la velocità è moderata (fase di puntamento), richiedi scansione UIA
        if self._uia_scanner is not None and self._current_velocity < 150.0:
            self._uia_scanner.request_inspection(x, y)

        # 5. Fallback immediato a Win32 WindowFromPoint per finestre e controlli nativi
        try:
            self._pt.x = int(round(x))
            self._pt.y = int(round(y))
            hwnd = user32.WindowFromPoint(self._pt)
            if hwnd and user32.IsWindowVisible(hwnd):
                if user32.GetWindowRect(hwnd, self._rect_byref):
                    w = self._rect.right - self._rect.left
                    h = self._rect.bottom - self._rect.top
                    area = w * h
                    # Filtra solo elementi di dimensioni tipiche di controlli GUI (pulsanti, input, icone)
                    # Scarta contenitori, pannelli e finestre ad alta area (Anti-Giant Container Trap)
                    if (MIN_SNAP_DIM <= w <= MAX_SNAP_WIDTH and
                            MIN_SNAP_DIM <= h <= MAX_SNAP_HEIGHT and
                            area <= MAX_SNAP_AREA):
                        # Assicura che il cursore sia vicino o dentro il rettangolo
                        if (self._rect.left - self.snap_radius <= x <= self._rect.right + self.snap_radius and
                                self._rect.top - self.snap_radius <= y <= self._rect.bottom + self.snap_radius):
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
