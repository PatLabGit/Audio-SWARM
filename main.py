#!/usr/bin/env python3
"""Audio-SWARM application entry point."""
from __future__ import annotations
import multiprocessing
import os
import sys
import tkinter as tk

_VENDOR_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if os.path.isdir(_VENDOR_DIR) and _VENDOR_DIR not in sys.path:
    sys.path.append(_VENDOR_DIR)


def create_root_window():
    """Enable optional tkinterdnd2 support when installed, otherwise use Tk."""
    try:
        from tkinterdnd2 import TkinterDnD
        return TkinterDnD.Tk()
    except (ImportError, RuntimeError, tk.TclError):
        stray = getattr(tk, "_default_root", None)
        if stray is not None:
            try:
                stray.destroy()
            except tk.TclError:
                pass
        return tk.Tk()


def main():
    # Imported lazily so spawned render workers don't load the whole GUI.
    from app.gui.app import AudioSWARMApp

    root = create_root_window()
    AudioSWARMApp(root)
    root.mainloop()


if __name__ == "__main__":
    multiprocessing.freeze_support()  # needed for frozen (PyInstaller) builds that use worker processes
    main()
