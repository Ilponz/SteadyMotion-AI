"""
Modulo Calcolo Bivariate Contour Ellipse Area (BCEA) & Indice di Stabilità Posturale.
Progettato per SteadyMotion AI v3.0.

Obiettivo Clinico:
Fornire al neurologo, fisiatra o terapista occupazionale una quantificazione oggettiva
della stabilità di fissazione cefalica o oculare durante la fase di calibrazione neutra.

Definizione Matematica (Standard Oftalmologico & Fisiologico):
Data una serie temporale di N campioni bidimensionali (x_i, y_i) (in gradi o pixel):
  BCEA = 2 * k * pi * sigma_x * sigma_y * sqrt(1 - rho^2)

dove:
- k = -ln(1 - P)
  - Per intervallo di confidenza 68% (1 deviazione standard): k = -ln(0.32) ~= 1.1394
  - Per intervallo di confidenza 95%: k = -ln(0.05) ~= 2.9957
- sigma_x, sigma_y = deviazioni standard degli scostamenti
- rho = coefficiente di correlazione lineare di Pearson tra gli assi X e Y

Algoritmo Online a Zero Heap Churn:
Accumula le somme parziali (N, sum_x, sum_y, sum_x2, sum_y2, sum_xy) in un unico passaggio O(1)
senza allocare array dinamici in memoria.
"""

import math
from typing import Dict, NamedTuple, Optional, Tuple


class BCEAResult(NamedTuple):
    samples_count: int
    mean_x: float
    mean_y: float
    sigma_x: float
    sigma_y: float
    rho: float
    bcea_68: float
    bcea_95: float
    stability_grade: str  # "ECCELLENTE", "BUONA", "MODERATA", "INSTABILE"


class BCEACalculator:
    """Calcolatore online della Bivariate Contour Ellipse Area."""

    K_68 = 1.13943428  # -ln(1 - 0.68)
    K_95 = 2.99573227  # -ln(1 - 0.95)

    def __init__(self):
        self.reset()

    def reset(self):
        """Azzera gli accumulatori parziali."""
        self.n: int = 0
        self.sum_x: float = 0.0
        self.sum_y: float = 0.0
        self.sum_x2: float = 0.0
        self.sum_y2: float = 0.0
        self.sum_xy: float = 0.0

    def add_sample(self, x: float, y: float):
        """Aggiunge un campione (x, y) all'accumulatore in O(1)."""
        self.n += 1
        self.sum_x += x
        self.sum_y += y
        self.sum_x2 += x * x
        self.sum_y2 += y * y
        self.sum_xy += x * y

    def compute(self) -> BCEAResult:
        """Calcola e restituisce le metriche BCEA e il grado clinico di stabilità."""
        if self.n < 3:
            return BCEAResult(
                samples_count=self.n,
                mean_x=0.0,
                mean_y=0.0,
                sigma_x=0.0,
                sigma_y=0.0,
                rho=0.0,
                bcea_68=0.0,
                bcea_95=0.0,
                stability_grade="NON_SUFFICIENTE",
            )

        n = float(self.n)
        mean_x = self.sum_x / n
        mean_y = self.sum_y / n

        var_x = max(0.0, (self.sum_x2 - (self.sum_x * self.sum_x) / n) / (n - 1.0))
        var_y = max(0.0, (self.sum_y2 - (self.sum_y * self.sum_y) / n) / (n - 1.0))

        sigma_x = math.sqrt(var_x)
        sigma_y = math.sqrt(var_y)

        cov_xy = (self.sum_xy - (self.sum_x * self.sum_y) / n) / (n - 1.0)

        denom = sigma_x * sigma_y
        if denom > 1e-9:
            rho = max(-0.9999, min(0.9999, cov_xy / denom))
        else:
            rho = 0.0

        ellipse_factor = math.sqrt(max(0.0, 1.0 - rho * rho))
        base_area = 2.0 * math.pi * sigma_x * sigma_y * ellipse_factor

        bcea_68 = base_area * self.K_68
        bcea_95 = base_area * self.K_95

        # Classificazione Stabilità (valida per unità in gradi angolari)
        # Se espressa in gradi^2:
        if bcea_68 <= 0.35:
            grade = "ECCELLENTE"
        elif bcea_68 <= 1.20:
            grade = "BUONA"
        elif bcea_68 <= 2.80:
            grade = "MODERATA"
        else:
            grade = "INSTABILE"

        return BCEAResult(
            samples_count=self.n,
            mean_x=mean_x,
            mean_y=mean_y,
            sigma_x=sigma_x,
            sigma_y=sigma_y,
            rho=rho,
            bcea_68=bcea_68,
            bcea_95=bcea_95,
            stability_grade=grade,
        )
