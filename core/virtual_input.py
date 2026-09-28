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
from typing import Tuple

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

SM_CXSCREEN = 0
SM_CYSCREEN = 1
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

# DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 (-4)
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4

ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


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
        self.refresh_screen_metrics()
        self.is_dragging = False

        # Pre-allocazione statica della struct per SendInput a zero heap churn
        extra = ULONG_PTR(0)
        flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
        mi = MOUSEINPUT(0, 0, 0, flags, 0, extra)
        self._move_input = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi))
        self._move_byref = ctypes.byref(self._move_input)
        self._input_size = ctypes.sizeof(INPUT)

    def __del__(self):
        disable_high_precision_timer()

    def refresh_screen_metrics(self):
        """Calcola l'estensione dell'intero desktop virtuale su monitor singolo o multiplo."""
        self.vx = float(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
        self.vy = float(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
        self.vw = float(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
        self.vh = float(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))

        if self.vw <= 0 or self.vh <= 0:
            self.vx = 0.0
            self.vy = 0.0
            self.vw = float(user32.GetSystemMetrics(SM_CXSCREEN))
            self.vh = float(user32.GetSystemMetrics(SM_CYSCREEN))

    def move_to_pixel(self, x: float, y: float):
        """
        Muove il cursore preservando le coordinate frazionarie sub-pixel.
        Esegue la mutazione diretta in memoria C senza alcuna allocazione heap in Python.
        """
        clamped_x = max(self.vx, min(self.vx + self.vw - 1.0, float(x)))
        clamped_y = max(self.vy, min(self.vy + self.vh - 1.0, float(y)))

        # Calcolo normalizzato sub-pixel a 16-bit
        norm_x = int(round((clamped_x - self.vx) * 65535.0 / max(1.0, self.vw)))
        norm_y = int(round((clamped_y - self.vy) * 65535.0 / max(1.0, self.vh)))

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
        extra = ULONG_PTR(0)
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
        """Esegue un doppio clic asincrono non bloccante (zero frame persi a 60 FPS)."""
        self.click("left")

        def _delayed_second_click():
            time.sleep(0.08)
            self.click("left")

        threading.Thread(target=_delayed_second_click, daemon=True, name="AsyncDoubleClick").start()

    def mouse_down(self, button: str = "left"):
        extra = ULONG_PTR(0)
        down_flag = MOUSEEVENTF_LEFTDOWN if button == "left" else MOUSEEVENTF_RIGHTDOWN
        mi = MOUSEINPUT(0, 0, 0, down_flag, 0, extra)
        inp = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi))
        user32.SendInput(1, ctypes.byref(inp), self._input_size)
        self.is_dragging = True

    def mouse_up(self, button: str = "left"):
        extra = ULONG_PTR(0)
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

    def send_unicode_char(self, char: str):
        """Invia caratteri Unicode direttamente alla finestra Windows attiva."""
        extra = ULONG_PTR(0)
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
        """Invia codici di tasto virtuale (es. VK_BACK, VK_RETURN, VK_SPACE)."""
        extra = ULONG_PTR(0)
        KEYEVENTF_KEYUP = 0x0002
        ki_down = KEYBDINPUT(vk_code, 0, 0, 0, extra)
        inp_down = INPUT(type=1, union=_INPUTunion(ki=ki_down))

        ki_up = KEYBDINPUT(vk_code, 0, KEYEVENTF_KEYUP, 0, extra)
        inp_up = INPUT(type=1, union=_INPUTunion(ki=ki_up))

        inputs = (INPUT * 2)(inp_down, inp_up)
        user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
