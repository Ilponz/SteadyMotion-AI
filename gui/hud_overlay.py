"""
HUD Overlay semi-trasparente e click-through per Dwell Click.
Disegna un indicatore radiale di progresso attorno al cursore del mouse
senza intercettare i clic (completamente permeabile grazie a WS_EX_TRANSPARENT).
"""

import ctypes
import math
import tkinter as tk
from typing import Optional

WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
GWL_EXSTYLE = -20


class DwellHUD:
    """Finestra overlay galleggiante per feedback visivo del clic a sosta."""

    def __init__(self, size: int = 80):
        self.size = size
        self.radius = size // 2
        self.root: Optional[tk.Toplevel] = None
        self.canvas: Optional[tk.Canvas] = None
        self.is_visible = False
        self.bg_color = "#010101"  # Colore chiave per trasparenza

    def init_window(self, master: tk.Tk):
        """Inizializza la finestra sovrapposta priva di bordi e trasparente."""
        self.root = tk.Toplevel(master)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-transparentcolor", self.bg_color)
        self.root.config(bg=self.bg_color)
        self.root.geometry(f"{self.size}x{self.size}+0+0")
        self.root.withdraw()

        # Canvas con sfondo trasparente
        self.canvas = tk.Canvas(
            self.root,
            width=self.size,
            height=self.size,
            bg=self.bg_color,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # Abilitazione click-through a livello Win32
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        if hwnd == 0:
            hwnd = self.root.winfo_id()

        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED
        )

    def show_progress(self, progress: float, cursor_x: int, cursor_y: int):
        """Aggiorna il cerchio di caricamento attorno alle coordinate del cursore."""
        if self.root is None or self.canvas is None:
            return

        if progress <= 0.01:
            if self.is_visible:
                self.root.withdraw()
                self.is_visible = False
            return

        # Sposta la finestra centrata sul cursore
        wx = cursor_x - self.radius
        wy = cursor_y - self.radius
        self.root.geometry(f"{self.size}x{self.size}+{wx}+{wy}")

        if not self.is_visible:
            self.root.deiconify()
            self.is_visible = True

        self.canvas.delete("all")

        # Cerchio guida esterno (grigio scuro)
        margin = 6
        self.canvas.create_oval(
            margin,
            margin,
            self.size - margin,
            self.size - margin,
            outline="#38bdf8",
            width=2,
        )

        # Arco di progresso (Cyan/Verde brillante)
        extent = -int(progress * 359)
        self.canvas.create_arc(
            margin,
            margin,
            self.size - margin,
            self.size - margin,
            start=90,
            extent=extent,
            outline="#10b981" if progress < 0.9 else "#ef4444",
            width=4,
            style="arc",
        )

    def hide(self):
        if self.root and self.is_visible:
            self.root.withdraw()
            self.is_visible = False
