"""
Modulo di Scorrimento Continuo ai Bordi dello Schermo (Edge Scrolling Controller).
Progettato specificamente per pazienti con tetraplegia, SLA e disabilità motorie gravi:
1. Consente di scorrere agevolmente documenti lunghi (PDF, pagine web, cartelle cliniche, chat)
   semplicemente posizionando il puntatore cefalico in prossimità del bordo superiore o inferiore.
2. Ritardo di attivazione Dwell configurabile (0.35s di default) per discriminare transiti rapidi
   volontari da sosta intenzionale di lettura/scorrimento.
3. Cadenza di scorrimento controllata e costante (Win32 MOUSEEVENTF_WHEEL).
4. Disattivazione immediata all'allontanamento dal bordo.
5. Inibizione del Dwell Clicker durante lo scorrimento attivo per evitare clic involontari.
"""

from typing import Callable, Optional, Tuple


class EdgeScrollController:
    """Controllore deterministico di scorrimento automatico ai bordi del display attivo."""

    def __init__(
        self,
        scroll_callback: Callable[[int], None],
        margin_px: int = 24,
        dwell_activation_delay: float = 0.35,
        scroll_interval: float = 0.14,
        is_enabled: bool = True,
    ):
        self.scroll_callback = scroll_callback
        self.margin_px = max(8, int(margin_px))
        self.dwell_activation_delay = max(0.1, float(dwell_activation_delay))
        self.scroll_interval = max(0.05, float(scroll_interval))
        self.is_enabled = is_enabled

        # Stato interno
        self.active_edge: Optional[str] = None  # "top" o "bottom"
        self.edge_enter_time: float = 0.0
        self.last_scroll_time: float = 0.0
        self.is_scrolling: bool = False
        self.total_scroll_events: int = 0

    def set_enabled(self, enabled: bool):
        self.is_enabled = bool(enabled)
        if not self.is_enabled:
            self.reset()

    def set_margin(self, margin_px: int):
        self.margin_px = max(8, min(80, int(margin_px)))

    def set_speed(self, scroll_interval: float):
        self.scroll_interval = max(0.05, min(0.50, float(scroll_interval)))

    def reset(self):
        """Azzera lo stato di sosta ai bordi."""
        self.active_edge = None
        self.edge_enter_time = 0.0
        self.last_scroll_time = 0.0
        self.is_scrolling = False

    def update(
        self,
        cursor_x: float,
        cursor_y: float,
        monitor_top: int,
        monitor_bottom: int,
        now: float,
    ) -> bool:
        """
        Valuta la posizione del cursore rispetto ai bordi verticale del monitor corrente.
        Se il cursore staziona oltre il margine per il tempo di sosta, emette lo scroll.
        Restituisce True se lo scorrimento è attivo.
        """
        if not self.is_enabled:
            if self.active_edge is not None:
                self.reset()
            return False

        # Rilevamento zona bordo
        current_edge: Optional[str] = None
        if cursor_y <= monitor_top + self.margin_px:
            current_edge = "top"
        elif cursor_y >= monitor_bottom - self.margin_px:
            current_edge = "bottom"

        # Cursore fuori dalla zona bordi: azzera immediatamente
        if current_edge is None:
            if self.active_edge is not None:
                self.reset()
            return False

        # Ingresso o cambio di bordo
        if self.active_edge != current_edge:
            self.active_edge = current_edge
            self.edge_enter_time = now
            self.last_scroll_time = now
            self.is_scrolling = False
            return False

        # Stazionamento oltre la soglia di attivazione
        time_in_edge = now - self.edge_enter_time
        if time_in_edge >= self.dwell_activation_delay:
            clicks = 1 if self.active_edge == "top" else -1
            if not self.is_scrolling:
                # Primo impulso di scroll al raggiungimento della soglia dwell
                self.is_scrolling = True
                try:
                    self.scroll_callback(clicks)
                    self.total_scroll_events += 1
                except Exception:
                    pass
                self.last_scroll_time = now
            elif now - self.last_scroll_time >= self.scroll_interval:
                # Impulsi successivi cadenzati a intervallo costante
                try:
                    self.scroll_callback(clicks)
                    self.total_scroll_events += 1
                except Exception:
                    pass
                self.last_scroll_time = now
            return True

        return False
