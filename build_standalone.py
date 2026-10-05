"""
Script di compilazione Standalone per SteadyMotion AI v3.0 con PyInstaller & CustomTkinter.
Include:
- Modello neurale MediaPipe face_landmarker.task
- Temi, font e asset completi di CustomTkinter v6
- Librerie native C++ (OpenCV, MediaPipe XNNPACK, PortAudio)
- Configurazione GUI senza console terminale (Windowed)
- Generazione automatica archivio portatile ZIP per chiavetta USB
"""

import os
import shutil
import subprocess
import sys
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILE = os.path.join(BASE_DIR, "models", "face_landmarker.task")
MAIN_SCRIPT = os.path.join(BASE_DIR, "main.py")


def build():
    if not os.path.exists(MODEL_FILE):
        print(f"ERRORE: Modello neurale non trovato in: {MODEL_FILE}")
        sys.exit(1)

    print("==================================================")
    print("Avvio Compilazione Standalone SteadyMotion AI v3.0")
    print("==================================================")

    datas_param = f"{MODEL_FILE};models"

    hidden_imports = [
        "--hidden-import", "mediapipe",
        "--hidden-import", "mediapipe.tasks",
        "--hidden-import", "mediapipe.tasks.python",
        "--hidden-import", "mediapipe.tasks.python.vision",
        "--hidden-import", "sounddevice",
        "--hidden-import", "_cffi_backend",
        "--hidden-import", "cv2",
        "--hidden-import", "darkdetect",
        "--collect-all", "customtkinter",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", "SteadyMotion-AI",
        "--onedir",
        "--noconsole",
        "--add-data", datas_param,
        *hidden_imports,
        "--clean",
        "--noconfirm",
        MAIN_SCRIPT,
    ]

    print("Comando di compilazione:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=BASE_DIR)

    if res.returncode == 0:
        dist_dir = os.path.join(BASE_DIR, "dist", "SteadyMotion-AI")
        exe_path = os.path.join(dist_dir, "SteadyMotion-AI.exe")

        # Assicura copia ridondante di models/ anche nella root della cartella dist
        dist_models = os.path.join(dist_dir, "models")
        if not os.path.exists(dist_models):
            shutil.copytree(os.path.join(BASE_DIR, "models"), dist_models)

        # Copia script di avvio rapido e diagnostica caregiver nella cartella portatile
        for extra_file in ("Avvia_EXE_Standalone.bat", "Verifica_Webcam_Caregiver.bat", "diagnostica_hardware.py"):
            src = os.path.join(BASE_DIR, extra_file)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(dist_dir, extra_file))

        # Generazione archivio ZIP portatile per chiavetta USB
        zip_path = os.path.join(BASE_DIR, "dist", "SteadyMotion-AI-v3.0-Portable.zip")
        print("\nCompressione pacchetto portatile in corso...")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(dist_dir):
                for file in files:
                    full_file = os.path.join(root, file)
                    rel_path = os.path.relpath(full_file, os.path.dirname(dist_dir))
                    zipf.write(full_file, rel_path)

        print("==================================================")
        print("COMPILAZIONE E PACKAGING COMPLETATI CON SUCCESSO!")
        print(f"Cartella Standalone: {dist_dir}")
        print(f"Eseguibile: {exe_path}")
        print(f"Archivio Portatile ZIP: {zip_path}")
        print("==================================================")
    else:
        print("\nERRORE durante la compilazione PyInstaller!")
        sys.exit(res.returncode)


if __name__ == "__main__":
    build()
