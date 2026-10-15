"""User-facing error reporting (FR-18): clear messages, no SQL, no stack traces."""
import logging
from tkinter import messagebox

from exceptions import BankError
from .i18n import tr

logger = logging.getLogger("bms")

GENERIC_MESSAGE = ("An unexpected error occurred and the action was not completed. "
                   "Details were written to the application log.")


def show_error(parent, exc: BaseException, title: str = "Error") -> None:
    if isinstance(exc, BankError):
        messagebox.showerror(tr(title), tr(str(exc)), parent=parent)
    else:
        logger.error("Unexpected error", exc_info=exc)
        messagebox.showerror(tr(title), tr(GENERIC_MESSAGE), parent=parent)
