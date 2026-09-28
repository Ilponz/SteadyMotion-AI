"""
HUD Overlay semi-trasparente e click-through ad alte prestazioni.
Ottimizzazioni implementate:
1. Stili Win32 estesi: WS_EX_TRANSPARENT, WS_EX_LAYERED, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW
   (la finestra è permeabile al 100%, non ruba mai il focus e non appare in Alt+Tab).
2. Riduzione del carico GPU/DWM: ridisegna il cerchio solo se il progresso varia
   in modo percettibile (soglia minima delta-progresso), azzerando l'overhead di compositing.
"""

import ctypes
import math
import tkinter as tk
from typing import Optional

WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
GWL_EXSTYLE = -20


class DwellHUD:
    """Finestra overlay galleggiante a zero carico di elaborazione."""

    def __init__(self, size: int = 80):
        self.size = size
        self.radius = size // 2
        self.root: Optional[tk.Toplevel] = None
        self.canvas: Optional[tk.Canvas] = None
        self.is_visible = False
        self.bg_color = "#010101"

        self.last_drawn_progress: float = -1.0
        self.last_x: int = -999
        self.last_y: int = -999

    def init_window(self, master: tk.Tk):
        """Inizializza la finestra sovrapposta senza bordi e trasparente."""
        self.root = tk.Toplevel(master)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", self.bg_color)
        self.root.config(bg=self.bg_color)
        self.root.geometry(f"{self.size}x{self.size}+0+0")
        self.root.withdraw()

        self.canvas = tk.Canvas(
            self.root,
            width=self.size,
            height=self.size,
            bg=self.bg_color,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # Configurazione stili Win32 completi
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        if hwnd == 0:
            hwnd = self.root.winfo_id()

        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        target_style = style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, target_style)

    def show_progress(self, progress: float, cursor_x: int, cursor_y: int):
        """Disegna il cerchio di caricamento solo in presenza di variazioni visibili."""
        if self.root is None or self.canvas is None:
            return

        if progress <= 0.01:
            if self.is_visible:
                self.root.withdraw()
                self.is_visible = False
                self.last_drawn_progress = -1.0
            return

        wx = cursor_x - self.radius
        wy = cursor_y - self.radius

        # Riposizionamento solo se il cursore si è spostato di almeno 2 pixel
        if abs(wx - self.last_x) >= 2 or abs(wy - self.last_y) >= 2 or not self.is_visible:
            self.root.geometry(f"{self.size}x{self.size}+{wx}+{wy}")
            self.last_x = wx
            self.last_y = wy

        if not self.is_visible:
            self.root.deiconify()
            self.is_visible = True

        # Ridisegno del cerchio solo se il progresso è variato di almeno l'1%
        if abs(progress - self.last_drawn_progress) < 0.015:
            return

        self.last_drawn_progress = progress
        self.canvas.delete("all")

        margin = 6
        # Guida esterna azzurra
        self.canvas.create_oval(
            margin,
            margin,
            self.size - margin,
            self.size - margin,
            outline="#38bdf8",
            width=2,
        )

        # Arco di progresso verde/rosso imminente
        extent = -int(progress * 359)
        color = "#10b981" if progress < 0.85 else "#f59e0b" if progress < 0.95 else "#ef4444"
        self.canvas.create_arc(
            margin,
            margin,
            self.size - margin,
            self.size - margin,
            start=90,
            extent=extent,
            outline=color,
            width=4,
            style="arc",
        )

    def hide(self):
        if self.root and self.is_visible:
            self.root.withdraw()
            self.is_visible = False
            self.last_drawn_progress = -1.0
