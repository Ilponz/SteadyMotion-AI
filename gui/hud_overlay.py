"""
HUD Overlay semi-trasparente e click-through ad alte prestazioni con supporto Ipovisione e Temi.
Ottimizzazioni implementate:
1. Stili Win32 estesi: WS_EX_TRANSPARENT, WS_EX_LAYERED, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW
   (la finestra è permeabile al 100%, non ruba mai il focus e non appare in Alt+Tab).
2. Riduzione del carico GPU/DWM: ridisegna il cerchio solo se il progresso varia
   in modo percettibile (soglia minima delta-progresso), azzerando l'overhead di compositing.
3. Palette cromatiche ad alto contrasto per ipovisione e monitor 4K ad alta risoluzione.
"""

import ctypes
import math
import tkinter as tk
from typing import Dict, Optional

WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080
GWL_EXSTYLE = -20

HUD_THEMES: Dict[str, Dict[str, any]] = {
    "Emerald": {
        "guide": "#38bdf8",
        "progress_normal": "#10b981",
        "progress_warn": "#f59e0b",
        "progress_imminent": "#ef4444",
        "width_guide": 2,
        "width_progress": 4,
    },
    "High-Contrast Amber": {
        "guide": "#ffffff",
        "progress_normal": "#fbbf24",
        "progress_warn": "#f97316",
        "progress_imminent": "#dc2626",
        "width_guide": 3,
        "width_progress": 6,
    },
    "Electric Cyan": {
        "guide": "#64748b",
        "progress_normal": "#06b6d4",
        "progress_warn": "#3b82f6",
        "progress_imminent": "#8b5cf6",
        "width_guide": 2,
        "width_progress": 4,
    },
    "Obsidian Violet": {
        "guide": "#475569",
        "progress_normal": "#a855f7",
        "progress_warn": "#ec4899",
        "progress_imminent": "#f43f5e",
        "width_guide": 2,
        "width_progress": 5,
    },
}


class DwellHUD:
    """Finestra overlay galleggiante a zero carico di elaborazione con temi di contrasto."""

    def __init__(self, size: int = 80, theme: str = "Emerald"):
        self.size = size
        self.radius = size // 2
        self.theme_name = theme if theme in HUD_THEMES else "Emerald"
        self.theme = HUD_THEMES[self.theme_name]
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

    def set_theme(self, theme_name: str):
        """Cambia la palette cromatica dell'HUD."""
        if theme_name in HUD_THEMES:
            self.theme_name = theme_name
            self.theme = HUD_THEMES[theme_name]
            self.last_drawn_progress = -1.0

    def set_size(self, size: int):
        """Aggiorna le dimensioni dell'overlay (utile per schermi 4K o ipovisione)."""
        self.size = max(50, min(160, int(size)))
        self.radius = self.size // 2
        if self.root and self.canvas:
            self.root.geometry(f"{self.size}x{self.size}+{self.last_x}+{self.last_y}")
            self.canvas.config(width=self.size, height=self.size)
            self.last_drawn_progress = -1.0

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

        margin = max(4, int(self.size * 0.08))
        # 1. Guida circolare esterna
        self.canvas.create_oval(
            margin,
            margin,
            self.size - margin,
            self.size - margin,
            outline=self.theme["guide"],
            width=self.theme["width_guide"],
        )

        # 2. Arco di progresso ad alto contrasto
        extent = -int(progress * 359)
        color = (
            self.theme["progress_normal"]
            if progress < 0.85
            else self.theme["progress_warn"]
            if progress < 0.95
            else self.theme["progress_imminent"]
        )
        self.canvas.create_arc(
            margin,
            margin,
            self.size - margin,
            self.size - margin,
            start=90,
            extent=extent,
            outline=color,
            width=self.theme["width_progress"],
            style="arc",
        )

    def hide(self):
        if self.root and self.is_visible:
            self.root.withdraw()
            self.is_visible = False
            self.last_drawn_progress = -1.0
