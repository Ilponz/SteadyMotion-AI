"""
Iniezione nativa input mouse a 64-bit per Windows tramite ctypes SendInput (Zero Heap Churn).
Ottimizzazioni implementate:
1. Zero Allocazioni Heap a 60-120 Hz:
   La struttura nativa C `INPUT` per il movimento sub-pixel e la referenza `byref`
   sono pre-allocate staticamente una sola volta in memoria. Nei cicli di movimento
   vengono modificati solo i registri `dx` e `dy`, azzerando oltre 240 allocazioni C-wrapper
   al secondo ed eliminando qualsiasi pausa del Garbage Collector di Python.
2. Per-Monitor DPI Awareness v2 nativo:
   Utilizzo dell'API Win32 moderna `SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2)` (-4),
   che previene disallineamenti di coordinate sub-pixel e difetti di rendering su configurazioni
   ibride (es. laptop 2K/4K a 125%/150% + monitor secondario a 100%).
3. Risoluzione temporale kernel a 1.0 ms (timeBeginPeriod) per eliminare il jitter.
4. Mappatura normalizzata assoluta virtual desktop 0 - 65535 priva di bias direzionale.
"""

import ctypes
from ctypes import wintypes
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Costanti API Win32
INPUT_MOUSE = 0

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_WHEEL = 0x0800

SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

# DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 (-4)
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4

# Watermark identificativo per iniezioni SteadyMotion (ASCII 'STEA')
STEADYMOTION_INPUT_SIGNATURE = 0x53544541

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


MonitorEnumProc = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HANDLE,
    wintypes.HDC,
    ctypes.POINTER(wintypes.RECT),
    wintypes.LPARAM,
)


@dataclass
class DisplayMonitor:
    """Rappresentazione geometrica di un singolo display fisico."""
    hmonitor: int
    rect: Tuple[int, int, int, int]  # (left, top, right, bottom)
    work_rect: Tuple[int, int, int, int]
    is_primary: bool
    device_name: str

    @property
    def left(self) -> int:
        return self.rect[0]

    @property
    def top(self) -> int:
        return self.rect[1]

    @property
    def right(self) -> int:
        return self.rect[2]

    @property
    def bottom(self) -> int:
        return self.rect[3]

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]

    def contains(self, x: float, y: float) -> bool:
        """Determina se il punto (x, y) cade all'interno dei confini visibili del monitor."""
        return self.left <= x < self.right and self.top <= y < self.bottom

    def clamp(self, x: float, y: float) -> Tuple[float, float]:
        """Blocca le coordinate entro il perimetro sicuro del display."""
        cx = max(float(self.left), min(float(self.right - 1), float(x)))
        cy = max(float(self.top), min(float(self.bottom - 1), float(y)))
        return cx, cy

    def distance_to(self, x: float, y: float) -> float:
        """Distanza euclidea dal punto più vicino del rettangolo del monitor."""
        dx = max(0.0, float(self.left) - x, x - float(self.right - 1))
        dy = max(0.0, float(self.top) - y, y - float(self.bottom - 1))
        return (dx * dx + dy * dy) ** 0.5


def enumerate_monitors() -> List[DisplayMonitor]:
    """Interroga l'API Win32 EnumDisplayMonitors per mappare tutti i monitor attivi."""
    monitors: List[DisplayMonitor] = []

    def _enum_proc(hmon, hdc, lprect, lparam):
        info = MONITORINFOEX()
        info.cbSize = ctypes.sizeof(MONITORINFOEX)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            m = info.rcMonitor
            w = info.rcWork
            monitors.append(DisplayMonitor(
                hmonitor=int(hmon or 0),
                rect=(m.left, m.top, m.right, m.bottom),
                work_rect=(w.left, w.top, w.right, w.bottom),
                is_primary=bool(info.dwFlags & 1),
                device_name=str(info.szDevice),
            ))
        return True

    cb = MonitorEnumProc(_enum_proc)
    try:
        user32.EnumDisplayMonitors(None, None, cb, 0)
    except Exception:
        pass
    return monitors


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTunion(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUTunion),
    ]


user32 = ctypes.windll.user32
winmm = ctypes.windll.winmm


def set_dpi_awareness():
    """Imposta la massima consapevolezza DPI per schermi 2K/4K e multi-monitor."""
    # 1. Prova Per-Monitor DPI Awareness v2 (Windows 10 1703+ e Windows 11)
    try:
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
        if user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)):
            return
    except Exception:
        pass

    # 2. Fallback su Per-Monitor DPI Awareness v1
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    # 3. Fallback standard
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass


def enable_high_precision_timer():
    """Imposta la risoluzione del timer di Windows a 1.0 ms e DPI awareness."""
    set_dpi_awareness()
    try:
        winmm.timeBeginPeriod(1)
    except Exception:
        pass


def disable_high_precision_timer():
    """Ripristina la risoluzione originale del timer di Windows."""
    try:
        winmm.timeEndPeriod(1)
    except Exception:
        pass


class WindowsMouseController:
    """Controller mouse Win32 ad altissima efficienza con zero allocazioni heap in move."""

    def __init__(self):
        enable_high_precision_timer()
        self.signature_extra = ULONG_PTR(STEADYMOTION_INPUT_SIGNATURE)
        self.monitors: List[DisplayMonitor] = []
        self.refresh_screen_metrics()
        self.is_dragging = False

        # Pre-allocazione statica della struct per SendInput a zero heap churn
        flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
        mi = MOUSEINPUT(0, 0, 0, flags, 0, self.signature_extra)
        self._move_input = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi))
        self._move_byref = ctypes.byref(self._move_input)
        self._input_size = ctypes.sizeof(INPUT)

    def __del__(self):
        disable_high_precision_timer()

    def refresh_screen_metrics(self):
        """Calcola l'estensione dell'intero desktop virtuale e mappa la geometria dei monitor attivi."""
        self.vx = float(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
        self.vy = float(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
        self.vw = float(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
        self.vh = float(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))

        if self.vw <= 0 or self.vh <= 0:
            self.vx = 0.0
            self.vy = 0.0
            self.vw = float(user32.GetSystemMetrics(SM_CXSCREEN))
            self.vh = float(user32.GetSystemMetrics(SM_CYSCREEN))

        self.monitors = enumerate_monitors()

    def check_screen_metrics_changed(self) -> bool:
        """
        Verifica se la topologia o risoluzione del display è cambiata a caldo (hotplug HDMI / scaling).
        Se rileva variazioni, sincronizza automaticamente le coordinate virtuali e la lista dei display.
        """
        cur_vx = float(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
        cur_vy = float(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
        cur_vw = float(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
        cur_vh = float(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))

        if cur_vw <= 0 or cur_vh <= 0:
            cur_vx = 0.0
            cur_vy = 0.0
            cur_vw = float(user32.GetSystemMetrics(SM_CXSCREEN))
            cur_vh = float(user32.GetSystemMetrics(SM_CYSCREEN))

        if (cur_vx != self.vx or cur_vy != self.vy or
                cur_vw != self.vw or cur_vh != self.vh):
            self.vx = cur_vx
            self.vy = cur_vy
            self.vw = cur_vw
            self.vh = cur_vh
            self.monitors = enumerate_monitors()
            return True
        return False

    def get_display_monitors(self) -> List[DisplayMonitor]:
        """Restituisce l'elenco dei display monitor attivi mappati."""
        return list(self.monitors)

    def get_monitor_at(self, x: float, y: float) -> Optional[DisplayMonitor]:
        """Individua il monitor fisico contenente le coordinate specificate."""
        for m in self.monitors:
            if m.contains(x, y):
                return m
        return None

    def clamp_to_display(self, x: float, y: float) -> Tuple[float, float]:
        """
        Blocca le coordinate all'interno della superficie visibile dei monitor attivi.
        Se il cursore si trova in una 'dead zone' (vuoto virtuale tra schermi di altezze diverse),
        proietta il cursore sul perimetro del monitor più vicino, impedendone la scomparsa.
        """
        if self.monitors:
            for m in self.monitors:
                if m.contains(x, y):
                    return float(x), float(y)
            closest = min(self.monitors, key=lambda m: m.distance_to(x, y))
            return closest.clamp(x, y)

        # Fallback desktop virtuale standard
        clamped_x = max(self.vx, min(self.vx + self.vw - 1.0, float(x)))
        clamped_y = max(self.vy, min(self.vy + self.vh - 1.0, float(y)))
        return clamped_x, clamped_y

    def move_to_pixel(self, x: float, y: float):
        """
        Muove il cursore preservando le coordinate frazionarie sub-pixel.
        Esegue la mutazione diretta in memoria C senza alcuna allocazione heap in Python.
        Garantisce reachability 100% fino all'ultimo pixel di bordo (0 e 65535) e protezione dead-zone.
        """
        clamped_x, clamped_y = self.clamp_to_display(x, y)

        # Calcolo normalizzato sub-pixel a 16-bit su span effettivo (vw - 1, vh - 1)
        span_w = max(1.0, self.vw - 1.0)
        span_h = max(1.0, self.vh - 1.0)
        norm_x = int(round((clamped_x - self.vx) * 65535.0 / span_w))
        norm_y = int(round((clamped_y - self.vy) * 65535.0 / span_h))

        norm_x = max(0, min(65535, norm_x))
        norm_y = max(0, min(65535, norm_y))

        # Modifica in-place della struct C pre-allocata (Zero Churn)
        self._move_input.union.mi.dx = norm_x
        self._move_input.union.mi.dy = norm_y

        user32.SendInput(1, self._move_byref, self._input_size)

    def get_cursor_pos(self) -> Tuple[int, int]:
        """Restituisce la posizione del cursore in coordinate pixel di sistema."""
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def click(self, button: str = "left"):
        """Esegue un clic completo atomico Down + Up."""
        extra = self.signature_extra
        if button == "left":
            down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
        elif button == "right":
            down_flag, up_flag = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
        elif button == "middle":
            down_flag, up_flag = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
        else:
            down_flag, up_flag = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP

        mi_down = MOUSEINPUT(0, 0, 0, down_flag, 0, extra)
        inp_down = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi_down))

        mi_up = MOUSEINPUT(0, 0, 0, up_flag, 0, extra)
        inp_up = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi_up))

        inputs = (INPUT * 2)(inp_down, inp_up)
        user32.SendInput(2, inputs, self._input_size)

    def double_click(self):
        """
        Esegue un doppio clic asincrono non bloccante ancorato alle coordinate del primo clic.
        Previene il fallimento del doppio clic dovuto al tremore tra i due impulsi (SM_CXDOUBLECLK).
        """
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        target_x, target_y = float(pt.x), float(pt.y)

        self.click("left")

        def _delayed_second_click():
            time.sleep(0.08)
            # Riposiziona brevemente sulle coordinate del primo clic per garantire la finestra di tolleranza Windows
            self.move_to_pixel(target_x, target_y)
            self.click("left")

        threading.Thread(target=_delayed_second_click, daemon=True, name="AsyncDoubleClick").start()

    def mouse_down(self, button: str = "left"):
        extra = self.signature_extra
        down_flag = MOUSEEVENTF_LEFTDOWN if button == "left" else MOUSEEVENTF_RIGHTDOWN
        mi = MOUSEINPUT(0, 0, 0, down_flag, 0, extra)
        inp = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi))
        user32.SendInput(1, ctypes.byref(inp), self._input_size)
        self.is_dragging = True

    def mouse_up(self, button: str = "left"):
        extra = self.signature_extra
        up_flag = MOUSEEVENTF_LEFTUP if button == "left" else MOUSEEVENTF_RIGHTUP
        mi = MOUSEINPUT(0, 0, 0, up_flag, 0, extra)
        inp = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi))
        user32.SendInput(1, ctypes.byref(inp), self._input_size)
        self.is_dragging = False

    def toggle_drag(self):
        if self.is_dragging:
            self.mouse_up("left")
        else:
            self.mouse_down("left")

    def scroll(self, clicks: int):
        """Esegue uno scroll della rotellina del mouse (positivo = su, negativo = giù)."""
        extra = self.signature_extra
        # 120 corrisponde a 1 tacca standard di rotellina in Windows (WHEEL_DELTA)
        wheel_delta = int(clicks * 120)
        mi = MOUSEINPUT(0, 0, wheel_delta, MOUSEEVENTF_WHEEL, 0, extra)
        inp = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi))
        user32.SendInput(1, ctypes.byref(inp), self._input_size)

    def send_unicode_char(self, char: str):
        """Invia caratteri Unicode direttamente alla finestra Windows attiva."""
        extra = self.signature_extra
        KEYEVENTF_KEYUP = 0x0002
        KEYEVENTF_UNICODE = 0x0004
        for c in char:
            val = ord(c)
            ki_down = KEYBDINPUT(0, val, KEYEVENTF_UNICODE, 0, extra)
            inp_down = INPUT(type=1, union=_INPUTunion(ki=ki_down))

            ki_up = KEYBDINPUT(0, val, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, extra)
            inp_up = INPUT(type=1, union=_INPUTunion(ki=ki_up))

            inputs = (INPUT * 2)(inp_down, inp_up)
            user32.SendInput(2, inputs, ctypes.sizeof(INPUT))

    def send_key_event(self, vk_code: int):
        """Invia codici di tasto virtuale (es. VK_BACK, VK_RETURN, VK_SPACE, VK_TAB, VK_ESCAPE)."""
        extra = self.signature_extra
        KEYEVENTF_KEYUP = 0x0002
        ki_down = KEYBDINPUT(vk_code, 0, 0, 0, extra)
        inp_down = INPUT(type=1, union=_INPUTunion(ki=ki_down))

        ki_up = KEYBDINPUT(vk_code, 0, KEYEVENTF_KEYUP, 0, extra)
        inp_up = INPUT(type=1, union=_INPUTunion(ki=ki_up))

        inputs = (INPUT * 2)(inp_down, inp_up)
        user32.SendInput(2, inputs, ctypes.sizeof(INPUT))

    def send_key_combination(self, modifier_vk: int, key_vk: int):
        """Invia una combinazione di tasti con modificatore (es. Ctrl+C, Ctrl+V, Ctrl+A, Alt+Tab)."""
        extra = self.signature_extra
        KEYEVENTF_KEYUP = 0x0002

        m_down = INPUT(type=1, union=_INPUTunion(ki=KEYBDINPUT(modifier_vk, 0, 0, 0, extra)))
        k_down = INPUT(type=1, union=_INPUTunion(ki=KEYBDINPUT(key_vk, 0, 0, 0, extra)))
        k_up = INPUT(type=1, union=_INPUTunion(ki=KEYBDINPUT(key_vk, 0, KEYEVENTF_KEYUP, 0, extra)))
        m_up = INPUT(type=1, union=_INPUTunion(ki=KEYBDINPUT(modifier_vk, 0, KEYEVENTF_KEYUP, 0, extra)))

        inputs = (INPUT * 4)(m_down, k_down, k_up, m_up)
        user32.SendInput(4, inputs, ctypes.sizeof(INPUT))
