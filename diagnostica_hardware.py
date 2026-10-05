"""
Script Standalone di Diagnostica Hardware per Caregiver e Collaudatori.
Esegue il check-up completo dei sensori webcam, FPS reali, luce ambientale e microfono.
Salva automaticamente il report in 'report_diagnostica_hardware.txt'.
"""

import os
import sys
from core.diagnostics import run_full_diagnostics, format_diagnostic_report_text

def main():
    print("\n" + "=" * 60)
    print("  Avvio Diagnostica Hardware SteadyMotion AI...")
    print("  Scansione webcam USB, misura FPS reali e rumore audio in corso...")
    print("=" * 60 + "\n")

    diag = run_full_diagnostics()
    report = format_diagnostic_report_text(diag)

    print(report)

    report_path = "report_diagnostica_hardware.txt"
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n[OK] Report salvato con successo in: {os.path.abspath(report_path)}")
    except Exception as e:
        print(f"\n[ATTENZIONE] Impossibile salvare il file di report: {e}")

    print("\nPremere Invio per uscire...")
    try:
        input()
    except Exception:
        pass

if __name__ == "__main__":
    main()
