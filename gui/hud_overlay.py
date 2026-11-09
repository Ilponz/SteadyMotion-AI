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
        self.last_offset_x: float = 0.0
        self.last_offset_y: float = 0.0
        self.is_last_danger: bool = False

        # Reticolo di Fissazione & Micro-Scatter Bio-Feedback
        self.show_reticle: bool = True
        self._scatter_history: list = [(0.0, 0.0)] * 8
        self._scatter_idx: int = 0
        self._scatter_count: int = 0

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

    def set_reticle_enabled(self, enabled: bool):
        """Attiva o disattiva il reticolo di stabilità posturale e lo scatter trail all'interno dell'HUD."""
        self.show_reticle = bool(enabled)
        self.last_drawn_progress = -1.0

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

    def show_progress(
        self,
        progress: float,
        cursor_x: int,
        cursor_y: int,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        tolerance_radius: float = 24.0,
        is_danger: bool = False,
    ):
        """Disegna il cerchio di caricamento e il reticolo di stabilità posturale con micro-scatter."""
        if self.root is None or self.canvas is None:
            return

        self.is_last_danger = bool(is_danger)

        if progress <= 0.01:
            if self.is_visible:
                self.root.withdraw()
                self.is_visible = False
                self.last_drawn_progress = -1.0
                self._scatter_count = 0
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

        # Ridisegno solo se progresso o micro-offset variano in modo percettibile
        prog_diff = abs(progress - self.last_drawn_progress) >= 0.012
        offset_diff = abs(offset_x - self.last_offset_x) >= 1.5 or abs(offset_y - self.last_offset_y) >= 1.5
        if not prog_diff and not offset_diff:
            return

        self.last_drawn_progress = progress
        self.last_offset_x = offset_x
        self.last_offset_y = offset_y

        # Aggiornamento storico micro-scatter (Zero Heap Churn)
        self._scatter_history[self._scatter_idx] = (float(offset_x), float(offset_y))
        self._scatter_idx = (self._scatter_idx + 1) % 8
        self._scatter_count = min(8, self._scatter_count + 1)

        self.canvas.delete("all")

        margin = max(4, int(self.size * 0.08))
        cx = self.size / 2.0
        cy = self.size / 2.0

        # Guida circolare: se in danger zone (chiusura/sistema), evidenzia in rosso allerta
        guide_color = "#EF4444" if is_danger else self.theme["guide"]
        guide_width = (self.theme["width_guide"] + 1) if is_danger else self.theme["width_guide"]

        # 1. Guida circolare esterna
        self.canvas.create_oval(
            margin,
            margin,
            self.size - margin,
            self.size - margin,
            outline=guide_color,
            width=guide_width,
        )

        # 2. Reticolo di Stabilità Posturale & Bio-Feedback Micro-Scatter
        if self.show_reticle:
            r_inner = self.radius - margin - 4
            r_tol_inner = max(8.0, min(r_inner * 0.72, r_inner * (float(tolerance_radius) / 34.0)))
            s_factor = r_tol_inner / max(1.0, float(tolerance_radius))

            # Cerchio tratteggiato soglia di tolleranza
            self.canvas.create_oval(
                cx - r_tol_inner,
                cy - r_tol_inner,
                cx + r_tol_inner,
                cy + r_tol_inner,
                outline=self.theme["guide"],
                width=1,
                dash=(2, 2),
            )

            # Mirino centrale di fissazione perfetta
            self.canvas.create_line(cx - 3, cy, cx + 3, cy, fill=self.theme["guide"], width=1)
            self.canvas.create_line(cx, cy - 3, cx, cy + 3, fill=self.theme["guide"], width=1)

            # Micro-trail di scostamento (fading scatter)
            if self._scatter_count > 1:
                for i in range(self._scatter_count - 1):
                    hist_idx = (self._scatter_idx - self._scatter_count + i) % 8
                    ox, oy = self._scatter_history[hist_idx]
                    sx = cx + ox * s_factor
                    sy = cy + oy * s_factor
                    d_s = math.hypot(sx - cx, sy - cy)
                    if d_s > r_inner:
                        sx = cx + (sx - cx) * (r_inner / d_s)
                        sy = cy + (sy - cy) * (r_inner / d_s)
                    self.canvas.create_oval(sx - 1, sy - 1, sx + 1, sy + 1, fill=self.theme["guide"], outline="")

            # Punto vivo di stabilità posturale
            px = cx + offset_x * s_factor
            py = cy + offset_y * s_factor
            d_p = math.hypot(px - cx, py - cy)
            if d_p > r_inner:
                px = cx + (px - cx) * (r_inner / d_p)
                py = cy + (py - cy) * (r_inner / d_p)

            dist_raw = math.hypot(offset_x, offset_y)
            if dist_raw <= 4.0:
                dot_col = self.theme["progress_normal"]
                dot_r = 3
            elif dist_raw <= tolerance_radius:
                dot_col = self.theme["progress_normal"] if progress < 0.85 else self.theme["progress_warn"]
                dot_r = 3
            else:
                dot_col = self.theme["progress_imminent"]
                dot_r = 4

            self.canvas.create_oval(
                px - dot_r,
                py - dot_r,
                px + dot_r,
                py + dot_r,
                fill=dot_col,
                outline="#ffffff" if dist_raw > tolerance_radius else dot_col,
                width=1,
            )

        # Segnale di sicurezza Danger Zone attivo (Pulsante X / Start Menu)
        if self.show_reticle and is_danger:
            tri_y = cy - r_inner * 0.42
            self.canvas.create_polygon(
                cx, tri_y - 6,
                cx + 7, tri_y + 6,
                cx - 7, tri_y + 6,
                fill="#EF4444",
                outline="#FFFFFF",
                width=1,
            )
            self.canvas.create_text(
                cx, tri_y + 1,
                text="!",
                font=("Segoe UI", 7, "bold"),
                fill="#FFFFFF",
            )

        # 3. Arco di progresso ad alto contrasto
        extent = -int(progress * 359)
        if is_danger:
            color = "#EF4444" if progress < 0.85 else "#DC2626"
        else:
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
        self._scatter_count = 0
        self.last_drawn_progress = -1.0
        if self.root and self.is_visible:
            self.root.withdraw()
            self.is_visible = False
