"""
Utility di sistema e risoluzione percorsi universale (Dev & PyInstaller Frozen).
"""

import os
import sys


def get_resource_path(relative_path: str) -> str:
    """
    Restituisce il percorso assoluto della risorsa richiesta.
    Risolve in modo infallibile in tutti gli ambienti:
    1. PyInstaller _MEIPASS (_internal o temporary bundle)
    2. Cartella contenente l'eseguibile compilato
    3. Sottocartella _internal dell'eseguibile (PyInstaller v6+)
    4. Ambiente di sviluppo nativo (cartella radice del repository)
    """
    candidates = []

    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            candidates.append(os.path.join(getattr(sys, "_MEIPASS"), relative_path))

        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, relative_path))
        candidates.append(os.path.join(exe_dir, "_internal", relative_path))

    # Fallback per ambiente di sviluppo Python nativo
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(repo_root, relative_path))

    for path in candidates:
        if os.path.exists(path):
            return os.path.normpath(path)

    # Restituisce il primo candidato se nessuno esiste ancora
    return os.path.normpath(candidates[0])
