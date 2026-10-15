
"""Login screen (UC-01) and first-run administrator setup."""

import tkinter as tk
import customtkinter as ctk

import config
from exceptions import BankError
from .errors import show_error
from .i18n import add_language_selector


# UI colors
BG_COLOR = "#0F172A"
CARD_COLOR = "#FFFFFF"
TEXT_COLOR = "#0F172A"
MUTED_COLOR = "#64748B"
ACCENT_COLOR = "#2563EB"
ERROR_COLOR = "#DC2626"


def _add_field(parent, row, label_text, variable, show=None):
    """Create a label and CustomTkinter input field."""

    label = ctk.CTkLabel(
        parent,
        text=label_text,
        text_color=TEXT_COLOR,
        anchor="w",
        font=("Segoe UI", 12, "bold"),
    )
    label.grid(
        row=row,
        column=0,
        sticky="ew",
        padx=24,
        pady=(10, 4),
    )

    entry = ctk.CTkEntry(
        parent,
        textvariable=variable,
        width=320,
        height=42,
        corner_radius=8,
        border_width=1,
        border_color="#CBD5E1",
        fg_color="#F8FAFC",
        text_color=TEXT_COLOR,
        placeholder_text=label_text,
        show=show,
    )
    entry.grid(
        row=row + 1,
        column=0,
        sticky="ew",
        padx=24,
        pady=(0, 6),
    )

    return entry


class _Card(ctk.CTkFrame):
    """Shared layout for login and administrator setup screens."""

    def __init__(self, parent, heading, subtitle):
        super().__init__(
            parent,
            fg_color=BG_COLOR,
            corner_radius=0,
        )

        card = ctk.CTkFrame(
            self,
            width=400,
            corner_radius=18,
            fg_color=CARD_COLOR,
            border_width=1,
            border_color="#E2E8F0",
        )
        card.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
        )

        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text=config.APP_NAME,
            text_color=ACCENT_COLOR,
            font=("Segoe UI", 24, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=24,
            pady=(28, 8),
        )

        ctk.CTkLabel(
            card,
            text=heading,
            text_color=TEXT_COLOR,
            font=("Segoe UI", 18, "bold"),
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 6),
        )

        ctk.CTkLabel(
            card,
            text=subtitle,
            text_color=MUTED_COLOR,
            font=("Segoe UI", 12),
            wraplength=320,
            justify="center",
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            padx=24,
            pady=(0, 12),
        )

        self.card = card

        self.error = ctk.CTkLabel(
            card,
            text="",
            text_color=ERROR_COLOR,
            wraplength=320,
            font=("Segoe UI", 12),
        )


class LoginView(_Card):
    def __init__(self, parent, ctx, on_success):
        super().__init__(
            parent,
            "Staff Sign In",
            config.APP_SUBTITLE,
        )

        self.ctx = ctx
        self.on_success = on_success
        add_language_selector(self.card, ctx.change_language, row=9, column=0, pady=(0, 18))

        self.username = tk.StringVar()
        self.password = tk.StringVar()

        user_entry = _add_field(
            self.card, 3, "Username", self.username
        )
        pass_entry = _add_field(
            self.card, 5, "Password", self.password, show="*"
        )

        self.error.grid(
            row=7,
            column=0,
            sticky="ew",
            padx=24,
            pady=(4, 0),
        )

        ctk.CTkButton(
            self.card,
            text="Sign In",
            height=44,
            corner_radius=8,
            fg_color=ACCENT_COLOR,
            hover_color="#1D4ED8",
            font=("Segoe UI", 13, "bold"),
            command=self.submit,
        ).grid(
            row=8,
            column=0,
            sticky="ew",
            padx=24,
            pady=(12, 28),
        )

        for entry in (user_entry, pass_entry):
            entry.bind("<Return>", lambda _event: self.submit())

        user_entry.focus_set()

    def submit(self):
        try:
            user = self.ctx.auth.login(
                self.username.get(),
                self.password.get(),
            )
        except BankError as exc:
            self.error.configure(text=str(exc))
            self.password.set("")
            return
        except Exception as exc:
            show_error(self, exc, "Sign In")
            return

        self.password.set("")
        self.on_success(user)


class FirstRunSetupView(_Card):
    def __init__(self, parent, ctx, on_done):
        super().__init__(
            parent,
            "First-time setup",
            "No staff accounts exist yet. Create the first administrator account.",
        )

        self.ctx = ctx
        self.on_done = on_done
        add_language_selector(self.card, ctx.change_language, row=12, column=0, pady=(0, 18))

        self.username = tk.StringVar()
        self.password = tk.StringVar()
        self.confirm = tk.StringVar()

        user_entry = _add_field(
            self.card, 3, "Username", self.username
        )
        _add_field(
            self.card, 5, "Password", self.password, show="*"
        )
        confirm_entry = _add_field(
            self.card, 7, "Confirm password", self.confirm, show="*"
        )

        ctk.CTkLabel(
            self.card,
            text=(
                f"Password must have at least "
                f"{config.MIN_PASSWORD_LENGTH} characters, "
                "including a letter and a digit."
            ),
            text_color=MUTED_COLOR,
            wraplength=320,
            font=("Segoe UI", 11),
            justify="left",
        ).grid(
            row=9,
            column=0,
            sticky="ew",
            padx=24,
            pady=(4, 0),
        )

        self.error.grid(
            row=10,
            column=0,
            sticky="ew",
            padx=24,
            pady=(6, 0),
        )

        ctk.CTkButton(
            self.card,
            text="Create Administrator",
            height=44,
            corner_radius=8,
            fg_color=ACCENT_COLOR,
            hover_color="#1D4ED8",
            font=("Segoe UI", 13, "bold"),
            command=self.submit,
        ).grid(
            row=11,
            column=0,
            sticky="ew",
            padx=24,
            pady=(12, 28),
        )

        for entry in (user_entry, confirm_entry):
            entry.bind("<Return>", lambda _event: self.submit())

        user_entry.focus_set()

    def submit(self):
        if self.password.get() != self.confirm.get():
            self.error.configure(text="Passwords do not match.")
            return

        try:
            self.ctx.auth.bootstrap_admin(
                self.username.get(),
                self.password.get(),
            )
        except BankError as exc:
            self.error.configure(text=str(exc))
            return
        except Exception as exc:
            show_error(self, exc, "Setup")
            return

        self.on_done()
