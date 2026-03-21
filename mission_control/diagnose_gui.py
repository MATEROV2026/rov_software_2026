#!/usr/bin/env python3
"""
Find which import aborts on macOS (dyld \"macOS … required\" messages).

Run from the project directory:
  python diagnose_gui.py

If the process dies before a numbered line, the *next* step is the culprit.

Common case (abort right after \"3 tkinter.Tk()\"):
  Your *Python build* ships Tcl/Tk (.framework or libtk) built for a *newer*
  macOS than the one you are running. That is not fixable from our app code.
  Fix: use a Python installer matched to your OS (Homebrew is reliable):

    brew install python@3.12
    /opt/homebrew/bin/python3.12 -m venv .venv   # Apple Silicon
    # Intel Mac often: /usr/local/opt/python@3.12/bin/python3.12 -m venv .venv

    source .venv/bin/activate
    pip install -U pip
    pip install -r requirements.txt
    python diagnose_gui.py
"""
from __future__ import annotations

import importlib.util
import sys


def main() -> None:
    print("0 ok — interpreter:", sys.executable, flush=True)
    print("1 pygame find_spec:", importlib.util.find_spec("pygame"), flush=True)

    print("2 import tkinter …", flush=True)
    import tkinter  # noqa: PLC0415

    print("3 tkinter.Tk() …", flush=True)
    import tkinter as tk

    r = tk.Tk()
    r.withdraw()
    r.destroy()
    print(
        "   Tcl/Tk OK (abort on step 3 → docstring / Homebrew python@3.12)",
        flush=True,
    )

    print("4 import customtkinter …", flush=True)
    import customtkinter  # noqa: PLC0415

    print("5 import urllib.request (stdlib) …", flush=True)
    import urllib.request  # noqa: F401, PLC0415

    print("6 all steps passed — run: python gui/app.py", flush=True)


if __name__ == "__main__":
    main()
