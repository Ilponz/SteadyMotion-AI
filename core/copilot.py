"""
Modulo Caregiver Co-Pilot: Arbitraggio e Risoluzione Conflitti con Mouse Fisico USB.
Progettato per SteadyMotion AI v3.0.

Obiettivo Clinico:
Evitare la tipica contesa del cursore ("Mouse Fight") tra il caregiver che tocca il mouse fisico
e il sistema di head-tracking che inietta coordinate assolute a 60 FPS.

Principio di Funzionamento:
1. Ad ogni frame di iniezione, confronta la posizione attuale del cursore di sistema (GetCursorPos)
   con l'ultima coordinata effettivamente iniettata da SteadyMotion nel frame precedente.
2. Se la discrepanza supera una soglia di sicurezza (es. > 24 px) senza che sia dovuta a scatti di rete,
   significa inequivocabilmente che un dispositivo fisico USB (mouse/trackpad) è stato mosso manualmente.
3. Il modulo attiva istantaneamente una pausa di cortesia di 2.0 secondi, congelando il tracciamento
   cefalico, emettendo un feedback acustico discreto e cedendo il pieno controllo all'operatore.
4. Quando il mouse fisico rimane fermo per la durata prevista, il controllo cefalico si riarma
   automaticamente senza scatti bruschi.
"""

from typing import Callable, Optional, Tuple


class CaregiverCoPilot:
    """Monitor di arbitraggio tra input cefalico virtuale e mouse fisico reale."""

    def __init__(
        self,
        threshold_px: float = 24.0,
        pause_duration: float = 2.0,
        on_override_start: Optional[Callable[[], None]] = None,
        on_override_end: Optional[Callable[[], None]] = None,
    ):
        self.threshold_px = float(threshold_px)
        self.pause_duration = float(pause_duration)
        self.on_override_start = on_override_start
        self.on_override_end = on_override_end

        self.last_injected_x: Optional[float] = None
        self.last_injected_y: Optional[float] = None
        self.pause_until: float = 0.0
        self.is_currently_overridden: bool = False
        self.is_enabled: bool = True

    def record_injection(self, x: float, y: float):
        """Registra la coordinata appena iniettata da SteadyMotion."""
        self.last_injected_x = float(x)
        self.last_injected_y = float(y)

    def check_override(self, actual_x: int, actual_y: int, now: float) -> bool:
        """
        Verifica se il mouse fisico è stato mosso da un operatore esterno.
        Restituisce True se il controllo è attualmente ceduto al caregiver.
        """
        if not self.is_enabled:
            return False

        # Se siamo già in pausa di cortesia
        if now < self.pause_until:
            # Continuiamo a monitorare se il caregiver si sta ancora muovendo per prolungare la pausa
            if self.last_injected_x is not None and self.last_injected_y is not None:
                dx = actual_x - self.last_injected_x
                dy = actual_y - self.last_injected_y
                dist = (dx * dx + dy * dy) ** 0.5
                if dist > 8.0:  # Movimento continuo del caregiver
                    self.pause_until = now + self.pause_duration
                    self.last_injected_x = float(actual_x)
                    self.last_injected_y = float(actual_y)
            return True

        # Se la pausa è appena terminata
        if self.is_currently_overridden and now >= self.pause_until:
            self.is_currently_overridden = False
            self.last_injected_x = float(actual_x)
            self.last_injected_y = float(actual_y)
            if self.on_override_end:
                self.on_override_end()
            return False

        # Verifica di nuovo spostamento fisico anomalo rispetto all'ultima iniezione
        if self.last_injected_x is not None and self.last_injected_y is not None:
            dx = actual_x - self.last_injected_x
            dy = actual_y - self.last_injected_y
            dist = (dx * dx + dy * dy) ** 0.5

            if dist > self.threshold_px:
                # Intervento Caregiver rilevato!
                self.is_currently_overridden = True
                self.pause_until = now + self.pause_duration
                self.last_injected_x = float(actual_x)
                self.last_injected_y = float(actual_y)
                if self.on_override_start:
                    self.on_override_start()
                return True

        return False
