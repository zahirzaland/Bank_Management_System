
"""Modern bank-management dashboard using CustomTkinter."""

import customtkinter as ctk

import config
from services import permissions

from .account_view import AccountView
from .customer_view import CustomerView
from .errors import show_error
from .interest_view import InterestView
from .loan_view import LoanView
from .report_view import ReportView
from .staff_view import StaffView
from .transaction_view import TransactionView
from .i18n import add_language_selector, get_language, tr


# -------------------- Theme --------------------

BG_COLOR = "#F7F8FC"
CONTENT_COLOR = "#F1F4FA"
SIDEBAR_COLOR = "#FFFFFF"
PANEL_COLOR = "#FFFFFF"
ACTIVE_COLOR = "#4F83F1"
ACTIVE_HOVER = "#3C70DA"
TEXT_COLOR = "#202938"
MUTED_COLOR = "#8A93A4"
BORDER_COLOR = "#E4E8F0"
SIDEBAR_HOVER = "#F0F5FF"
GREEN = "#16A37A"
RED = "#DC5263"
SOFT_BLUE = "#E2E9FC"


NAV = (
    ("Customers", CustomerView, "view", "♙"),
    ("Accounts", AccountView, "view", "▣"),
    ("Transactions", TransactionView, "view", "⇄"),
    ("Loans", LoanView, "manage_loans", "$"),
    ("Interest", InterestView, "manage_interest", "%"),
    ("Reports", ReportView, "reports", "▤"),
    ("Staff", StaffView, "manage_staff", "♧"),
)


class DashboardView(ctk.CTkFrame):
    """Dashboard shell. Existing business views remain unchanged."""

    def __init__(self, parent, ctx, on_logout):
        super().__init__(
            parent,
            fg_color=BG_COLOR,
            corner_radius=0,
        )

        self.ctx = ctx
        self.on_logout = on_logout
        self.current = None
        self.current_name = None
        self.buttons = {}

        rtl = get_language() == "ps"
        self.grid_columnconfigure((0, 1), weight=0)
        self.grid_columnconfigure(0 if rtl else 1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

        # Overview is the initial page.
        self.show("Overview", None)

    # -------------------- Sidebar --------------------

    def _build_sidebar(self):
        side = ctk.CTkFrame(
            self,
            width=215,
            fg_color=SIDEBAR_COLOR,
            corner_radius=0,
        )
        side.grid(row=0, column=1 if get_language() == "ps" else 0, sticky="nsew")
        side.grid_propagate(False)

        brand = ctk.CTkFrame(
            side,
            fg_color="transparent",
        )
        brand.pack(fill="x", padx=16, pady=(24, 6))

        ctk.CTkLabel(
            brand,
            text="NB",
            width=40,
            height=40,
            corner_radius=10,
            fg_color=SOFT_BLUE,
            text_color=ACTIVE_COLOR,
            font=("Segoe UI", 18, "bold"),
        ).pack(side="left")

        brand_text = ctk.CTkFrame(
            brand,
            fg_color="transparent",
        )
        brand_text.pack(side="left", padx=9)

        ctk.CTkLabel(
            brand_text,
            text=config.APP_NAME,
            text_color=TEXT_COLOR,
            font=("Segoe UI", 13, "bold"),
            anchor="w",
            wraplength=125,
        ).pack(anchor="w")

        ctk.CTkLabel(
            brand_text,
            text="BANKING SYSTEM",
            text_color=MUTED_COLOR,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(anchor="w", pady=(3, 0))

        ctk.CTkLabel(
            side,
            text="WORKSPACE",
            text_color=MUTED_COLOR,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", padx=20, pady=(32, 10))

        self._nav_button(
            side, "Overview", None, "▦"
        )

        for name, view_cls, permission, icon in NAV:
            if permissions.can(self.ctx.user, permission):
                self._nav_button(
                    side, name, view_cls, icon
                )

        ctk.CTkFrame(
            side,
            fg_color="transparent",
        ).pack(fill="both", expand=True)

        user_box = ctk.CTkFrame(
            side,
            fg_color="#F7F8FC",
            corner_radius=10,
        )
        user_box.pack(
            fill="x",
            padx=12,
            pady=(8, 8),
        )

        username = getattr(
            self.ctx.user, "username", "User"
        )
        role = getattr(
            self.ctx.user, "role", "Staff"
        )

        ctk.CTkLabel(
            user_box,
            text=str(username),
            text_color=TEXT_COLOR,
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(fill="x", padx=11, pady=(10, 2))

        ctk.CTkLabel(
            user_box,
            text=str(role),
            text_color=MUTED_COLOR,
            font=("Segoe UI", 10),
            anchor="w",
        ).pack(fill="x", padx=11, pady=(0, 10))

    def _nav_button(self, parent, name, view_cls, icon):
        rtl = get_language() == "ps"
        button = ctk.CTkButton(
            parent,
            text=f"{tr(name)}    {icon}" if rtl else f"{icon}    {tr(name)}",
            height=42,
            corner_radius=9,
            anchor="e" if rtl else "w",
            fg_color="transparent",
            hover_color=SIDEBAR_HOVER,
            text_color="#566174",
            font=("Segoe UI", 11),
            command=lambda n=name, v=view_cls:
                self.show(n, v),
        )
        button.pack(fill="x", padx=11, pady=3)
        self.buttons[name] = button

    # -------------------- Main area --------------------

    def _build_main_area(self):
        main = ctk.CTkFrame(
            self,
            fg_color=BG_COLOR,
            corner_radius=0,
        )
        main.grid(row=0, column=0 if get_language() == "ps" else 1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(
            main,
            height=68,
            fg_color=PANEL_COLOR,
            corner_radius=0,
        )
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        self.page_title = ctk.CTkLabel(
            header,
            text="OVERVIEW",
            text_color=TEXT_COLOR,
            font=("Segoe UI", 17, "bold"),
            anchor="w",
        )
        self.page_title.grid(
            row=0,
            column=0,
            sticky="w",
            padx=22,
        )

        ctk.CTkLabel(
            header,
            text=(f"{getattr(self.ctx.user, 'username', 'User')}  "
                  f"•  {tr(getattr(self.ctx.user, 'role', 'Staff'))}"),
            text_color=MUTED_COLOR,
            font=("Segoe UI", 10),
        ).grid(row=0, column=1, padx=18)

        ctk.CTkButton(
            header,
            text="Change Password",
            height=34,
            corner_radius=8,
            fg_color=ACTIVE_COLOR,
            hover_color=ACTIVE_HOVER,
            command=self.change_password,
        ).grid(row=0, column=2, padx=(0, 18))

        ctk.CTkButton(
            header,
            text="Log Out",
            height=34,
            corner_radius=8,
            fg_color="#DC5263",
            hover_color="#C83E50",
            text_color="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
            command=self.on_logout,
        ).grid(row=0, column=3, padx=(0, 18))

        add_language_selector(
            header, self.ctx.change_language,
            row=0, column=4, padx=(0, 14),
        )

        self.content = ctk.CTkFrame(
            main,
            fg_color=CONTENT_COLOR,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )
        self.content.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=12,
            pady=12,
        )
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    # -------------------- Navigation --------------------

    def show(self, name, view_cls):
        """Display exactly one selected page."""

        if self.current is not None:
            self.current.destroy()
            self.current = None

        self.current_name = name
        self.page_title.configure(text=tr(name).upper())

        for key, button in self.buttons.items():
            active = key == name
            button.configure(
                fg_color=ACTIVE_COLOR if active else "transparent",
                hover_color=(
                    ACTIVE_HOVER if active else SIDEBAR_HOVER
                ),
                text_color=(
                    "#FFFFFF" if active else "#566174"
                ),
                font=(
                    "Segoe UI",
                    11,
                    "bold" if active else "normal",
                ),
            )

        if view_cls is None:
            self._build_overview()
            return

        self.current = view_cls(self.content, self.ctx)
        self.current.pack(fill="both", expand=True)
    def show(self, name, view_cls):
        """Display exactly one selected page."""

        if self.current is not None:
            self.current.destroy()
            self.current = None

        self.current_name = name
        self.page_title.configure(text=name.upper())

        for key, button in self.buttons.items():
            active = key == name
            button.configure(
                fg_color=ACTIVE_COLOR if active else "transparent",
                hover_color=ACTIVE_HOVER if active else SIDEBAR_HOVER,
                text_color="#FFFFFF" if active else "#566174",
                font=(
                    "Segoe UI",
                    11,
                    "bold" if active else "normal",
                ),
            )

        if name == "Overview":
            self._build_overview()
            return

        self.current = view_cls(self.content, self.ctx)
        self.current.pack(fill="both", expand=True)


    # -------------------- Overview --------------------

    def _panel(self, parent, title, subtitle=None):
        panel = ctk.CTkFrame(
            parent,
            fg_color=PANEL_COLOR,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_COLOR,
        )

        ctk.CTkLabel(
            panel,
            text=title,
            text_color=TEXT_COLOR,
            font=("Segoe UI", 13, "bold"),
            anchor="w",
        ).pack(fill="x", padx=15, pady=(14, 3))

        if subtitle:
            ctk.CTkLabel(
                panel,
                text=subtitle,
                text_color=MUTED_COLOR,
                font=("Segoe UI", 10),
                anchor="w",
                wraplength=600,
                justify="left",
            ).pack(fill="x", padx=15, pady=(0, 10))

        return panel


    def _build_overview(self):
        """Build Overview from real ReportService data."""

        root = ctk.CTkScrollableFrame(
            self.content,
            fg_color="transparent",
            corner_radius=0,
        )
        root.grid(row=0, column=0, sticky="nsew")
        root.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="metric")

        # Keep a reference so navigation destroys the entire Overview.
        self.current = root

        ctk.CTkLabel(
            root,
            text="Bank Overview",
            text_color=TEXT_COLOR,
            font=("Segoe UI", 22, "bold"),
            anchor="w",
        ).grid(
            row=0, column=0, columnspan=4,
            sticky="w", padx=5, pady=(5, 2),
        )

        ctk.CTkLabel(
            root,
            text="Real-time summary from your banking records",
            text_color=MUTED_COLOR,
            font=("Segoe UI", 11),
            anchor="w",
        ).grid(
            row=1, column=0, columnspan=4,
            sticky="w", padx=5, pady=(0, 18),
        )

        # Respect the existing report permission.
        if not permissions.can(self.ctx.user, "reports"):
            self._overview_message(
                root,
                "Reports permission is required to view these statistics.",
                row=2,
            )
            return

        try:
            _, transaction_rows = self.ctx.reports.generate(
                self.ctx.user, "Transaction Summary"
            )
            _, account_rows = self.ctx.reports.generate(
                self.ctx.user, "Account Summary"
            )
        except Exception as exc:
            self._overview_message(
                root,
                f"Could not load dashboard data: {exc}",
                row=2,
            )
            return

        transactions = {
            row[0]: row for row in transaction_rows
        }
        total_tx = transactions.get(
            "All transactions", ["", "0", "0"]
        )
        customers = transactions.get(
            "Customers registered", ["", "0", "-"]
        )
        deposits = transactions.get(
            "Deposits", ["", "0", "0"]
        )
        withdrawals = transactions.get(
            "Withdrawals", ["", "0", "0"]
        )
        transfers = transactions.get(
            "Transfers", ["", "0", "0"]
        )

        # Account Summary columns:
        # Account Type, Status, Count, Current Balance
        total_accounts = sum(
            self._to_number(row[2])
            for row in account_rows
        )
        total_balance = sum(
            self._to_number(row[3])
            for row in account_rows
        )

        currency = config.CURRENCY
        metrics = [
            (
                "Customers",
                customers[1],
                "Registered customers",
                ACTIVE_COLOR,
            ),
            (
                "Accounts",
                f"{total_accounts:,.0f}",
                "Accounts in the system",
                "#8B6CE8",
            ),
            (
                "Transactions",
                total_tx[1],
                "Recorded transactions",
                GREEN,
            ),
            (
                "Total Balance",
                f"{currency} {total_balance:,.2f}",
                "Current account balances",
                "#D99A35",
            ),
        ]

        for col, (title, value, description, color) in enumerate(metrics):
            card = ctk.CTkFrame(
                root,
                fg_color=PANEL_COLOR,
                corner_radius=12,
                border_width=1,
                border_color=BORDER_COLOR,
            )
            card.grid(
                row=2, column=col, sticky="nsew",
                padx=5, pady=(0, 15),
            )

            ctk.CTkLabel(
                card,
                text=title,
                text_color=MUTED_COLOR,
                font=("Segoe UI", 10, "bold"),
                anchor="w",
            ).pack(fill="x", padx=13, pady=(15, 5))

            ctk.CTkLabel(
                card,
                text=value,
                text_color=color,
                font=("Segoe UI", 20, "bold"),
                anchor="w",
                wraplength=180,
            ).pack(fill="x", padx=13, pady=3)

            ctk.CTkLabel(
                card,
                text=description,
                text_color=MUTED_COLOR,
                font=("Segoe UI", 9),
                anchor="w",
                wraplength=180,
            ).pack(fill="x", padx=13, pady=(3, 15))

        # Chart 1: transaction amount by type.
        amount_items = [
            ("Deposits", self._to_number(deposits[2]), ACTIVE_COLOR),
            ("Withdrawals", self._to_number(withdrawals[2]), RED),
            ("Transfers", self._to_number(transfers[2]), GREEN),
        ]

        amount_panel = self._panel(
            root,
            "Transaction Amounts",
            f"Transaction totals by type ({currency}).",
        )
        amount_panel.grid(
            row=3, column=0, columnspan=4,
            sticky="ew", padx=5, pady=(0, 15),
        )
        self._draw_bar_chart(amount_panel, amount_items, currency)

        # Chart 2: transaction count by type.
        count_items = [
            ("Deposits", self._to_number(deposits[1]), ACTIVE_COLOR),
            ("Withdrawals", self._to_number(withdrawals[1]), RED),
            ("Transfers", self._to_number(transfers[1]), GREEN),
        ]

        count_panel = self._panel(
            root,
            "Transaction Counts",
            "Number of recorded transactions by type.",
        )
        count_panel.grid(
            row=4, column=0, columnspan=4,
            sticky="ew", padx=5, pady=(0, 15),
        )
        self._draw_bar_chart(count_panel, count_items)

        # Quick navigation to existing modules.
        quick = self._panel(
            root,
            "Quick Access",
            "Open a module to manage its records.",
        )
        quick.grid(
            row=5, column=0, columnspan=4,
            sticky="ew", padx=5, pady=(0, 12),
        )

        actions = ctk.CTkFrame(
            quick, fg_color="transparent"
        )
        actions.pack(fill="x", padx=12, pady=(0, 14))

        # Derive Quick Access from the role-filtered navigation so permitted
        # modules (including Loans and Interest) are not accidentally omitted.
        available_views = [
            (name, view_cls)
            for name, view_cls, _permission, _icon in NAV
            if name in self.buttons
        ]

        for name, view in available_views:
            if name in self.buttons:
                ctk.CTkButton(
                    actions,
                    text=name,
                    height=36,
                    corner_radius=8,
                    fg_color=SOFT_BLUE,
                    hover_color="#D5DFFC",
                    text_color=ACTIVE_COLOR,
                    command=lambda n=name, v=view: self.show(n, v),
                ).pack(
                    side="right" if get_language() == "ps" else "left", fill="x",
                    expand=True, padx=4,
                )

    @staticmethod
    def _to_number(value):
        """Convert formatted numeric text into a number."""
        import re

        try:
            cleaned = re.sub(r"[^0-9.\-]", "", str(value).replace(",", ""))
            return float(cleaned) if cleaned else 0.0
        except (TypeError, ValueError):
            return 0.0

    def _overview_message(self, parent, message, row=2):
        ctk.CTkLabel(
            parent,
            text=message,
            text_color=RED,
            font=("Segoe UI", 12),
            wraplength=700,
            justify="left",
        ).grid(
            row=row, column=0, columnspan=4,
            sticky="w", padx=8, pady=20,
        )

    def _draw_bar_chart(self, panel, items, currency=None):
        """Draw a lightweight horizontal bar chart without extra libraries."""

        chart_area = ctk.CTkFrame(
            panel,
            fg_color="transparent",
        )
        chart_area.pack(fill="x", padx=15, pady=(0, 15))
        chart_area.grid_columnconfigure(1, weight=1)

        max_value = max(
            (value for _, value, _ in items),
            default=0,
        )

        for row_index, (label, value, color) in enumerate(items):
            ctk.CTkLabel(
                chart_area,
                text=label,
                text_color=TEXT_COLOR,
                font=("Segoe UI", 11),
                anchor="w",
                width=95,
            ).grid(
                row=row_index, column=0,
                sticky="w", padx=(0, 10), pady=9,
            )

            track = ctk.CTkFrame(
                chart_area,
                height=14,
                fg_color="#EDF0F6",
                corner_radius=7,
            )
            track.grid(
                row=row_index, column=1,
                sticky="ew", pady=9,
            )
            track.grid_propagate(False)

            ratio = value / max_value if max_value > 0 else 0
            if ratio > 0:
                bar = ctk.CTkFrame(
                    track,
                    height=14,
                    fg_color=color,
                    corner_radius=7,
                )
                bar.place(
                    relx=0,
                    rely=0,
                    relwidth=ratio,
                    relheight=1,
                )

            if currency:
                display_value = f"{currency} {value:,.2f}"
            else:
                display_value = f"{value:,.0f}"

            ctk.CTkLabel(
                chart_area,
                text=display_value,
                text_color=TEXT_COLOR,
                font=("Segoe UI", 10, "bold"),
                anchor="e",
                width=125,
            ).grid(
                row=row_index, column=2,
                sticky="e", padx=(10, 0), pady=9,
            )


    # -------------------- Change password --------------------

    def change_password(self):
        window = ctk.CTkToplevel(self)
        window.title("Change Password")
        window.geometry("440x510")
        window.resizable(False, False)
        window.transient(self.winfo_toplevel())
        window.grab_set()

        window.update_idletasks()
        parent = self.winfo_toplevel()
        parent.update_idletasks()

        x = parent.winfo_rootx() + (
            parent.winfo_width() - 440
        ) // 2
        y = parent.winfo_rooty() + (
            parent.winfo_height() - 510
        ) // 2
        window.geometry(f"+{max(x, 0)}+{max(y, 0)}")

        card = ctk.CTkFrame(
            window,
            corner_radius=16,
        )
        card.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(
            card,
            text="Change Password",
            font=("Segoe UI", 23, "bold"),
            text_color=TEXT_COLOR,
        ).pack(pady=(22, 5))

        ctk.CTkLabel(
            card,
            text="Update your account security",
            text_color=MUTED_COLOR,
            font=("Segoe UI", 12),
        ).pack(pady=(0, 20))

        fields = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )
        fields.pack(fill="x", padx=24)
        fields.grid_columnconfigure(0, weight=1)

        variables = [
            ctk.StringVar(),
            ctk.StringVar(),
            ctk.StringVar(),
        ]
        entries = []

        for row, (label, variable) in enumerate(
            zip(
                ("Current Password", "New Password",
                 "Confirm New Password"),
                variables,
            )
        ):
            ctk.CTkLabel(
                fields,
                text=label,
                font=("Segoe UI", 12, "bold"),
                anchor="w",
            ).grid(
                row=row * 2,
                column=0,
                sticky="w",
                pady=(0, 5),
            )

            entry = ctk.CTkEntry(
                fields,
                textvariable=variable,
                show="*",
                height=39,
                corner_radius=8,
                placeholder_text=label,
            )
            entry.grid(
                row=row * 2 + 1,
                column=0,
                sticky="ew",
                pady=(0, 12),
            )
            entries.append(entry)

        show_var = ctk.BooleanVar(value=False)

        def toggle_passwords():
            mask = "" if show_var.get() else "*"
            for entry in entries:
                entry.configure(show=mask)

        ctk.CTkCheckBox(
            card,
            text="Show passwords",
            variable=show_var,
            command=toggle_passwords,
        ).pack(anchor="w", padx=25, pady=(0, 12))

        message = ctk.CTkLabel(
            card,
            text="",
            text_color=RED,
            font=("Segoe UI", 10),
        )
        message.pack(pady=(0, 5))

        def submit():
            current, new, confirm = [
                variable.get() for variable in variables
            ]

            if not current or not new or not confirm:
                message.configure(
                    text="Please fill in all fields."
                )
                return

            if new != confirm:
                message.configure(
                    text="The new passwords do not match."
                )
                entries[2].focus_set()
                return

            if current == new:
                message.configure(
                    text="Choose a different new password."
                )
                return

            try:
                self.ctx.auth.change_own_password(
                    self.ctx.user,
                    current,
                    new,
                )
            except Exception as exc:
                show_error(window, exc, "Change Password")
                return

            from tkinter import messagebox

            messagebox.showinfo(
                "Success",
                "Your password was changed successfully.",
                parent=window,
            )
            window.destroy()

        footer = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )
        footer.pack(fill="x", padx=24, pady=(4, 18))

        ctk.CTkButton(
            footer,
            text="Cancel",
            height=39,
            fg_color="transparent",
            border_width=1,
            text_color=TEXT_COLOR,
            command=window.destroy,
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(
            footer,
            text="Change Password",
            height=39,
            command=submit,
        ).pack(side="left", fill="x", expand=True, padx=(5, 0))

        entries[0].focus_set()
        window.bind("<Escape>", lambda _event: window.destroy())
