"""
Utility di sistema e risoluzione percorsi universale (Dev, Portable & PyInstaller Frozen).
Garantisce la separazione tra risorse statiche di sola lettura (installate in Program Files o _internal)
e percorsi dati mutabili scrivibili dall'utente (%LOCALAPPDATA%\\SteadyMotion AI).
"""

import os
import sys


def get_resource_path(relative_path: str) -> str:
    """
    Restituisce il percorso assoluto della risorsa statica richiesta (modelli, template, suoni).
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


def get_user_data_dir(app_name: str = "SteadyMotion AI") -> str:
    """
    Restituisce la cartella dati dell'utente per file di configurazione, licenze e relazioni cliniche.
    Se l'applicazione è installata in una cartella protetta di sistema (es. C:\\Program Files),
    reindirizza in modo trasparente su %LOCALAPPDATA%\\SteadyMotion AI per prevenire PermissionError.
    Se invece l'applicazione viene eseguita come pacchetto portatile USB o in dev con permessi di scrittura,
    utilizza la directory locale dell'eseguibile.
    """
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    exe_dir_lower = exe_dir.lower()
    is_system_dir = (
        "program files" in exe_dir_lower or
        "system32" in exe_dir_lower or
        "windows" in exe_dir_lower
    )

    # Se non è in cartella di sistema ed è esplicitamente portatile o ha permessi di scrittura locale
    if not is_system_dir:
        # Se c'è un marker 'portable.txt' o '.portable' forza la modalità locale USB
        if (os.path.exists(os.path.join(exe_dir, "portable.txt")) or
                os.path.exists(os.path.join(exe_dir, ".portable"))):
            return os.path.normpath(exe_dir)

        # In modalità sviluppo o cartella utente libera, prova a scrivere un file temporaneo
        try:
            test_file = os.path.join(exe_dir, ".__write_test__")
            with open(test_file, "w") as tf:
                tf.write("ok")
            os.remove(test_file)
            return os.path.normpath(exe_dir)
        except Exception:
            pass

    # Directory di sistema (Program Files) o cartella di sola lettura: usa %LOCALAPPDATA%
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        local_appdata = os.path.expanduser("~")
    user_dir = os.path.join(local_appdata, app_name)
    os.makedirs(user_dir, exist_ok=True)
    return os.path.normpath(user_dir)


def get_user_data_path(relative_path: str) -> str:
    """
    Risolve un file di dati o configurazione all'interno della cartella dati utente.
    Crea automaticamente le directory genitrici necessarie.
    """
    base_dir = get_user_data_dir()
    full_path = os.path.join(base_dir, relative_path)
    os.makedirs(os.path.dirname(os.path.abspath(full_path)), exist_ok=True)
    return os.path.normpath(full_path)
