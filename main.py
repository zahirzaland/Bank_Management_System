"""Entry point: python main.py"""
import logging
import sys
from logging.handlers import RotatingFileHandler

import config
from database import Database
from services import build_services


def setup_logging() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("bms")
    root.setLevel(logging.INFO)
    root.propagate = False

    for handler in list(root.handlers):
        if isinstance(handler, RotatingFileHandler) and getattr(handler, "baseFilename", None) == str(config.LOG_PATH):
            return
        root.removeHandler(handler)

    handler = RotatingFileHandler(config.LOG_PATH, maxBytes=512_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)


def main() -> int:
    try:
        from ui.app import App  # checked first so a missing Tk gives a clear message
    except ImportError as exc:
        print(f"Tkinter is not available ({exc}). Install Python with Tk support "
              "(on Debian/Ubuntu: sudo apt install python3-tk).", file=sys.stderr)
        return 1

    setup_logging()
    db = Database(config.DB_PATH)
    try:
        db.initialize()
        App(build_services(db)).mainloop()
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())






