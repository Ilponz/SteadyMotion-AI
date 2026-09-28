"""
Iniezione nativa input mouse a 64-bit per Windows tramite ctypes SendInput.
Supporta puntamento assoluto su monitor singolo o multi-schermo virtuale,
bypass delle limitazioni di frame rate e compatibilità con finestre di sistema.
"""

import ctypes
from ctypes import wintypes
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

# Tipo ULONG_PTR dipendente dall'architettura (64-bit su x64)
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


class WindowsMouseController:
    """Controller nativo per iniezione di eventi mouse ad alta velocità su Windows."""

    def __init__(self):
        self.refresh_screen_metrics()
        self.is_dragging = False

    def refresh_screen_metrics(self):
        """Rileva le dimensioni del display virtuale (supporto per monitor singoli e multipli)."""
        self.vx = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        self.vy = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        self.vw = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        self.vh = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)

        if self.vw == 0 or self.vh == 0:
            self.vx = 0
            self.vy = 0
            self.vw = user32.GetSystemMetrics(SM_CXSCREEN)
            self.vh = user32.GetSystemMetrics(SM_CYSCREEN)

    def move_to_pixel(self, x: int, y: int):
        """Muove il cursore su coordinate pixel assolute dello schermo."""
        # Limita alle dimensioni del display
        clamped_x = max(self.vx, min(self.vx + self.vw - 1, int(x)))
        clamped_y = max(self.vy, min(self.vy + self.vh - 1, int(y)))

        # Normalizzazione nello spazio normalizzato 0 - 65535
        norm_x = int((clamped_x - self.vx) * 65535 / (self.vw - 1))
        norm_y = int((clamped_y - self.vy) * 65535 / (self.vh - 1))

        extra = ULONG_PTR(0)
        flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
        mi = MOUSEINPUT(norm_x, norm_y, 0, flags, 0, extra)
        inp = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi))

        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    def move_to_normalized(self, nx: float, ny: float):
        """Muove il cursore da coordinate normalizzate [0.0, 1.0]."""
        px = int(self.vx + nx * self.vw)
        py = int(self.vy + ny * self.vh)
        self.move_to_pixel(px, py)

    def get_cursor_pos(self) -> Tuple[int, int]:
        """Restituisce la posizione attuale del cursore in pixel."""
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def click(self, button: str = "left"):
        """Esegue un clic completo (down + up)."""
        extra = ULONG_PTR(0)
        if button == "left":
            down_flag = MOUSEEVENTF_LEFTDOWN
            up_flag = MOUSEEVENTF_LEFTUP
        elif button == "right":
            down_flag = MOUSEEVENTF_RIGHTDOWN
            up_flag = MOUSEEVENTF_RIGHTUP
        elif button == "middle":
            down_flag = MOUSEEVENTF_MIDDLEDOWN
            up_flag = MOUSEEVENTF_MIDDLEUP
        else:
            down_flag = MOUSEEVENTF_LEFTDOWN
            up_flag = MOUSEEVENTF_LEFTUP

        # Evento Down
        mi_down = MOUSEINPUT(0, 0, 0, down_flag, 0, extra)
        inp_down = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi_down))

        # Evento Up
        mi_up = MOUSEINPUT(0, 0, 0, up_flag, 0, extra)
        inp_up = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi_up))

        inputs = (INPUT * 2)(inp_down, inp_up)
        user32.SendInput(2, inputs, ctypes.sizeof(INPUT))

    def double_click(self):
        """Esegue un doppio clic rapido con intervallo fisiologico di 80 ms."""
        self.click("left")
        time.sleep(0.08)
        self.click("left")

    def mouse_down(self, button: str = "left"):
        """Pressione continuata del tasto (per drag and drop)."""
        extra = ULONG_PTR(0)
        down_flag = MOUSEEVENTF_LEFTDOWN if button == "left" else MOUSEEVENTF_RIGHTDOWN
        mi = MOUSEINPUT(0, 0, 0, down_flag, 0, extra)
        inp = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi))
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        self.is_dragging = True

    def mouse_up(self, button: str = "left"):
        """Rilascio del tasto premuto."""
        extra = ULONG_PTR(0)
        up_flag = MOUSEEVENTF_LEFTUP if button == "left" else MOUSEEVENTF_RIGHTUP
        mi = MOUSEINPUT(0, 0, 0, up_flag, 0, extra)
        inp = INPUT(type=INPUT_MOUSE, union=_INPUTunion(mi=mi))
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        self.is_dragging = False

    def toggle_drag(self):
        """Commuta lo stato di trascinamento (Latch Drag & Drop)."""
        if self.is_dragging:
            self.mouse_up("left")
        else:
            self.mouse_down("left")
