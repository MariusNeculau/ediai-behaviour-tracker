"""report_storage.py — unde și cum se salvează rapoartele generate.

Salvează fișierele într-un folder `Rapoarte_Salvate/` lângă aplicație (lângă .exe
când e frozen, altfel rădăcina proiectului), în loc să le trimită ca download.
"""

import os

import config

FOLDER_NAME = "Rapoarte_Salvate"


def reports_dir():
    """Folderul de salvare; lângă .exe când e frozen, altfel rădăcina proiectului."""
    return os.path.join(config.app_data_dir(), FOLDER_NAME)


def save_report(filename, data):
    """Scrie `data` (bytes) în reports_dir()/filename; întoarce calea absolută."""
    folder = reports_dir()
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path
