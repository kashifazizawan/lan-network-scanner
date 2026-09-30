"""Application logging. Never logs credentials or sensitive data."""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime


def setup_logging(level=logging.INFO) -> str:
    """Configure file + console logging. Returns the log file path."""
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.local/share")
    folder = os.path.join(base, "LanScanner")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"lanscanner_{datetime.now():%Y%m%d}.log")

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)

    fh = logging.FileHandler(path, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)
    return path


def install_excepthook(msgbox=None):
    """Replace the default excepthook so users see friendly errors, not tracebacks."""
    def hook(exc_type, exc, tb):
        logging.getLogger("lanscanner").exception("Unhandled error", exc_info=(exc_type, exc, tb))
        text = (
            "An unexpected error occurred:\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            "The error has been written to the application log."
        )
        if msgbox is not None:
            msgbox(text)
        else:
            sys.__excepthook__(exc_type, exc, tb)
    sys.excepthook = hook
