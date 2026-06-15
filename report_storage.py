"""report_storage.py — unde și cum se salvează rapoartele generate.

Salvează fișierele într-un folder `Rapoarte_Salvate/` lângă aplicație (lângă .exe
când e frozen, altfel rădăcina proiectului), în loc să le trimită ca download.
"""

import os
from datetime import datetime

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


def list_saved_reports():
    """Fișierele din Rapoarte_Salvate/, cele mai noi primele.

    Întoarce [{"filename": str, "generated": "dd Mon yyyy HH:MM"}], sortate
    descrescător după data modificării. [] dacă folderul nu există.
    """
    folder = reports_dir()
    if not os.path.isdir(folder):
        return []
    entries = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        mtime = os.path.getmtime(path)
        entries.append({
            "filename": name,
            "generated": datetime.fromtimestamp(mtime).strftime("%d %b %Y %H:%M"),
            "_mtime": mtime,
        })
    entries.sort(key=lambda e: e["_mtime"], reverse=True)
    for e in entries:
        del e["_mtime"]
    return entries
