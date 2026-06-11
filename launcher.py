"""launcher.py — entry-point pentru build-ul .exe.

Pornește serverul Flask FĂRĂ reloader (reloader-ul nu funcționează frozen) și
deschide automat browserul. În dezvoltare folosește în continuare `python app.py`.
"""

import threading
import webbrowser

from app import app

URL = "http://127.0.0.1:5000/"


def _open_browser():
    webbrowser.open(URL)


if __name__ == "__main__":
    threading.Timer(1.5, _open_browser).start()
    print(f"EDI AI Behaviour Tracker running at {URL}  (close this window to stop)")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
