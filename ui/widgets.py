
"""Reusable CustomTkinter widgets and a base class for screens."""

import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from services import permissions
from .errors import show_error
from .i18n import tr
from .i18n import get_language


OK_COLOR = "#238636"
ERR_COLOR = "#da3633"
MUTED_COLOR = ("#64748b", "#a1a1aa")


class DataTable(ctk.CTkFrame):
    """A responsive, theme-aware table with scrollbars.

    Columns: (heading, width, anchor)
    Rows: (iid, values)
    """

    def __init__(
        self,
        parent,
        columns,
        height=12,
        on_select=None,
        on_double_click=None,
    ):
        super().__init__(
            parent,
            corner_radius=10,
            border_width=1,
            border_color=("gray80", "gray25"),
            fg_color=("#ffffff", "#1e1e1e")
        )

        self._columns = list(columns)
        self._tree_height = height

        # Table container expands in both directions.
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            self,
            show="headings",
            selectmode="browse",
            height=height,
        )

        self.ysb = ctk.CTkScrollbar(
            self,
            orientation="vertical",
            command=self.tree.yview,
            width=14,
        )

        self.xsb = ctk.CTkScrollbar(
            self,
            orientation="horizontal",
            command=self.tree.xview,
            height=14,
        )

        self.tree.configure(
            yscrollcommand=self.ysb.set,
            xscrollcommand=self.xsb.set,
        )

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self.ysb.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.xsb.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        # Set initial style and column configuration.
        self._configure_style()
        self.set_columns(self._columns)

        # Alternating row backgrounds.
        self.tree.tag_configure(
            "even",
            background=self._colors()["row"],
            foreground=self._colors()["text"],
        )
        self.tree.tag_configure(
            "odd",
            background=self._colors()["alternate"],
            foreground=self._colors()["text"],
        )

        if on_select:
            self.tree.bind(
                "<<TreeviewSelect>>",
                lambda _event: on_select(),
            )

        if on_double_click:
            self.tree.bind(
                "<Double-1>",
                lambda _event: on_double_click(),
            )

    def _colors(self):
        """Return table colors for the current appearance mode."""

        dark = ctk.get_appearance_mode().lower() == "dark"

        if dark:
            return {
                "background": "#202020",
                "text": "#f5f5f5",
                "heading": "#303030",
                "selected": "#1f6aa5",
                "row": "#242424",
                "alternate": "#2b2b2b",
                "border": "#454545",
            }

        return {
            "background": "#ffffff",
            "text": "#202020",
            "heading": "#e9edf2",
            "selected": "#2563eb",
            "row": "#ffffff",
            "alternate": "#f3f6fa",
            "border": "#d1d5db",
        }

    def _configure_style(self):
        """Style the ttk table to visually match CustomTkinter."""

        colors = self._colors()
        style = ttk.Style(self)

        # 'clam' allows more reliable background and heading styling.
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "Bank.Treeview",
            background=colors["row"],
            fieldbackground=colors["background"],
            foreground=colors["text"],
            borderwidth=0,
            rowheight=36,
            font=("Segoe UI", 11),
        )

        style.configure(
            "Bank.Treeview.Heading",
            background=colors["heading"],
            foreground=colors["text"],
            font=("Segoe UI", 11, "bold"),
            padding=(10, 10),
            relief="flat",
            borderwidth=0,
        )

        style.map(
            "Bank.Treeview",
            background=[
                ("selected", colors["selected"]),
            ],
            foreground=[
                ("selected", "#ffffff"),
            ],
        )

        style.map(
            "Bank.Treeview.Heading",
            background=[
                ("active", colors["selected"]),
            ],
            foreground=[
                ("active", "#ffffff"),
            ],
        )

        self.tree.configure(
            style="Bank.Treeview",
        )

    def refresh_theme(self):
        """Refresh colors after the application appearance changes."""

        self._configure_style()
        colors = self._colors()

        self.tree.tag_configure(
            "even",
            background=colors["row"],
            foreground=colors["text"],
        )
        self.tree.tag_configure(
            "odd",
            background=colors["alternate"],
            foreground=colors["text"],
        )

    def set_columns(self, columns):
        """Configure table headings, alignment, and widths."""

        self._columns = list(columns)
        display_columns = list(reversed(self._columns)) if get_language() == "ps" else self._columns
        keys = [f"c{i}" for i in range(len(display_columns))]

        self.tree.configure(columns=keys)

        for key, (heading, width, anchor) in zip(
            keys,
            display_columns,
        ):
            self.tree.heading(
                key,
                text=tr(heading),
                anchor="e" if get_language() == "ps" and anchor != "center" else anchor,
            )

            self.tree.column(
                key,
                width=max(80, width),
                minwidth=60,
                anchor="e" if get_language() == "ps" and anchor != "center" else anchor,
                stretch=True,
            )

    def set_rows(self, rows):
        """Replace rows and preserve the selected item when possible."""

        previous = self.selected()

        self.tree.delete(*self.tree.get_children())

        for index, (iid, values) in enumerate(rows):
            display_values = list(reversed(values)) if get_language() == "ps" else list(values)
            self.tree.insert(
                "",
                "end",
                iid=str(iid),
                values=[tr(value) for value in display_values],
                tags=("even" if index % 2 == 0 else "odd",),
            )

        if previous is not None and self.tree.exists(previous):
            self.tree.selection_set(previous)
            self.tree.focus(previous)

    def selected(self):
        """Return the selected row ID or None."""

        selection = self.tree.selection()
        return selection[0] if selection else None

    def select(self, iid):
        """Select and scroll to a row."""

        iid = str(iid)

        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.focus(iid)
            self.tree.see(iid)

    def clear_selection(self):
        """Clear the current selection."""

        self.tree.selection_remove(self.tree.selection())


class BaseView(ctk.CTkFrame):
    """Base class for dashboard screens."""

    def __init__(self, parent, ctx):
        super().__init__(
            parent,
            corner_radius=0,
            fg_color=("#f8fafc", "#0f172a")
        )

        self.ctx = ctx
        self.grid_columnconfigure(0, weight=1)

    @property
    def user(self):
        return self.ctx.user

    def can(self, permission: str) -> bool:
        return permissions.can(
            self.ctx.user,
            permission,
        )

    def fail(self, exc: BaseException) -> None:
        show_error(self, exc)

    def title(self, text: str):
        """Display a consistent screen title."""

        rtl = get_language() == "ps"
        label = ctk.CTkLabel(
            self,
            text=tr(text),
            font=ctk.CTkFont(
                size=26,
                weight="bold",
            ),
            anchor="e" if rtl else "w",
        )

        label.pack(
            anchor="e" if rtl else "w",
            fill="x",
            padx=16,
            pady=(12, 16),
        )

        return label

    def readonly_notice(self, text: str = None) -> None:
        """Display a read-only permission notice."""

        rtl = get_language() == "ps"

        message = text or (
            f"Your role ({self.user.role}) "
            "has read-only access to this screen."
        )

        ctk.CTkLabel(
            self,
            text=message,
            text_color=MUTED_COLOR,
            anchor="e" if rtl else "w",
            wraplength=900,
        ).pack(
            anchor="e" if rtl else "w",
            fill="x",
            padx=16,
            pady=(0, 10),
        )


def add_field(
    parent,
    row,
    label,
    variable,
    width=32,
    show=None,
    state="normal",
    column=0,
):
    """Create a consistently styled label and entry."""

    rtl = get_language() == "ps"
    ctk.CTkLabel(
        parent,
        text=label,
        anchor="e" if rtl else "w",
    ).grid(
        row=row,
        column=column + 1 if rtl else column,
        sticky="e" if rtl else "w",
        padx=(0, 12) if rtl else (12, 10),
        pady=7,
    )

    entry = ctk.CTkEntry(
        parent,
        textvariable=variable,
        width=max(160, width * 8),
        height=36,
        show=show or "",
        state=state,
    )

    entry.grid(
        row=row,
        column=column if rtl else column + 1,
        sticky="ew",
        padx=(12, 0) if rtl else (0, 12),
        pady=7,
    )

    # Allow the entry column to expand with its parent.
    parent.grid_columnconfigure(
        column if rtl else column + 1,
        weight=1,
    )

    return entry


def set_message(label, text: str, ok: bool = True) -> None:
    """Display a success or error message."""

    label.configure(
        text=text,
        text_color=OK_COLOR if ok else ERR_COLOR,
    )


