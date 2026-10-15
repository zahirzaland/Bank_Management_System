"""Tk root window: styles, screen switching, session handling."""
import customtkinter as ctk
from tkinter import messagebox, ttk

import config
from .dashboard_view import DashboardView
from .errors import GENERIC_MESSAGE, logger
from .login_view import FirstRunSetupView, LoginView
from .i18n import add_language_selector, get_language, install_widget_translation, set_language, tr


class App(ctk.CTk):
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    def __init__(self, ctx):
        super().__init__()
        install_widget_translation()
        self.ctx = ctx
        try:
            set_language(config.DATA_DIR.joinpath("language.txt").read_text(encoding="utf-8").strip())
        except OSError:
            set_language("en")
        ctx.request_logout = self.logout
        ctx.change_language = self.change_language
        self._idle_after_id = None
        self.bind_all("<KeyPress>", self._reset_idle_timer, add="+")
        self.bind_all("<Button>", self._reset_idle_timer, add="+")
        self.bind_all("<MouseWheel>", self._reset_idle_timer, add="+")
        self.bind_all("<Motion>", self._reset_idle_timer, add="+")
        self.title(f"{tr(config.APP_NAME)} - {tr('Educational Simulation')}")
        self.geometry("1180x720")
        self.minsize(960, 600)
        self._configure_styles()
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self.show_login()

    def change_language(self, language):
        if language == get_language():
            return
        set_language(language)
        self.title(f"{tr(config.APP_NAME)} - {tr('Educational Simulation')}")
        try:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            config.DATA_DIR.joinpath("language.txt").write_text(language, encoding="utf-8")
        except OSError:
            logger.exception("Could not save language preference")
        if self.ctx.user is None:
            self.show_login()
        else:
            self.on_login(self.ctx.user)

    def report_callback_exception(self, exc, val, tb):  # unexpected errors inside Tk callbacks
        logger.error("Unhandled UI error", exc_info=(exc, val, tb))
        messagebox.showerror("Error", GENERIC_MESSAGE, parent=self)


    def _configure_styles(self):
        style = ttk.Style(self)

        # Use a theme that supports custom background colors
        if "classic" in style.theme_names():
            style.theme_use("classic")

        base = (
            "Segoe UI"
            if self.tk.call("tk", "windowingsystem") == "win32"
            else "Helvetica"
        )

        style.configure(
            ".",
            font=(base, 10),
            background="#F1F5F9",
        )

        style.configure(
            "Title.TLabel",
            font=(base, 18, "bold"),
            background="#FFFFFF",
            foreground="#0F172A",
        )

        style.configure(
            "Sub.TLabel",
            font=(base, 11, "bold"),
            background="#FFFFFF",
            foreground="#334155",
        )

        style.configure(
            "Card.TFrame",
            background="#FFFFFF",
            relief="solid",
            borderwidth=1,
        )

        style.configure(
            "Side.TFrame",
            background="#1F2A44",
        )

        style.configure(
            "SideTitle.TLabel",
            background="#1F2A44",
            foreground="white",
            font=(base, 13, "bold"),
        )

        style.configure(
            "Nav.TButton",
            anchor="w",
            padding=8,
            background="#1F2A44",
            foreground="white",
            borderwidth=0,
        )
        style.map(
            "Nav.TButton",
            background=[("active", "#33436B")],
        )

        style.configure(
            "NavActive.TButton",
            anchor="w",
            padding=8,
            background="#3F5CA8",
            foreground="white",
            borderwidth=0,
        )
        style.map(
            "NavActive.TButton",
            background=[("active", "#4A69BD")],
        )

        style.configure(
            "Accent.TButton",
            font=(base, 10, "bold"),
        )

        style.configure("Treeview", rowheight=24)
        style.configure(
            "Treeview.Heading",
            font=(base, 10, "bold"),
        )

    def _clear(self):
        for child in self.container.winfo_children():
            child.destroy()

    def show_login(self):
        self._clear()
        if self.ctx.auth.needs_bootstrap():
            view = FirstRunSetupView(self.container, self.ctx, on_done=self.show_login)
        else:
            view = LoginView(self.container, self.ctx, on_success=self.on_login)
        view.pack(fill="both", expand=True)

    def on_login(self, user):
        self.ctx.user = user
        self._clear()
        DashboardView(self.container, self.ctx, on_logout=self.logout).pack(fill="both", expand=True)
        self._reset_idle_timer()

    def _reset_idle_timer(self, _event=None):
        if self._idle_after_id is not None:
            self.after_cancel(self._idle_after_id)
            self._idle_after_id = None
        if self.ctx.user is not None:
            self._idle_after_id = self.after(
                config.IDLE_TIMEOUT_SECONDS * 1000, self._on_idle_timeout)

    def _on_idle_timeout(self):
        self._idle_after_id = None
        if self.ctx.user is not None:
            self.logout()
            messagebox.showinfo(
                "Session expired",
                "You were signed out after a period of inactivity.",
                parent=self)

    def logout(self):
        if self._idle_after_id is not None:
            self.after_cancel(self._idle_after_id)
            self._idle_after_id = None
        user, self.ctx.user = self.ctx.user, None
        if user:
            try:
                self.ctx.auth.logout(user)
            except Exception:
                logger.exception("Could not write logout audit entry")
        self.show_login()
