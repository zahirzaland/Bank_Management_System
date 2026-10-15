"""Account opening and status management (FR-07, FR-08, FR-12, UC-03)."""

import customtkinter as ctk
from tkinter import messagebox

import config
from exceptions import BankError
from utils import format_money, parse_money
from .widgets import BaseView, DataTable, set_message
from .i18n import tr, untr


class AccountView(BaseView):
    def __init__(self, parent, ctx):
        super().__init__(parent, ctx)

        self.customer_lookup = {}
        self.find_var = ctk.StringVar()
        self.customer_var = ctk.StringVar()
        self.type_var = ctk.StringVar(value=tr(config.ACCOUNT_TYPES[0]))
        self.opening_var = ctk.StringVar(value="0.00")
        self.search_var = ctk.StringVar()
        self.filter_var = ctk.StringVar(value=tr("All"))

        self.title("Accounts")

        # Open a new account
        if self.can("manage_accounts"):
            box = ctk.CTkFrame(
                self,
                corner_radius=10,
                fg_color="#FFFFFF",
                border_width=1,
                border_color="#E4E8F0",
            )
            box.pack(fill="x", padx=10, pady=5)

            ctk.CTkLabel(
                box,
                text="Open a New Account",
                font=ctk.CTkFont(size=17, weight="bold")
            ).grid(row=0, column=0, columnspan=3,
                   sticky="w", padx=12, pady=(12, 8))

            box.grid_columnconfigure(1, weight=1)

            ctk.CTkLabel(
                box, text="Find customer (ID or name)"
            ).grid(row=1, column=0, sticky="w", padx=12, pady=5)

            find_entry = ctk.CTkEntry(
                box,
                textvariable=self.find_var,
                width=240,
                placeholder_text="Enter customer ID or name"
            )
            find_entry.grid(row=1, column=1, sticky="ew", padx=6, pady=5)
            find_entry.bind("<Return>", lambda _e: self.find_customers())

            ctk.CTkButton(
                box,
                text="Find",
                width=90,
                command=self.find_customers
            ).grid(row=1, column=2, padx=12, pady=5)

            ctk.CTkLabel(
                box, text="Customer"
            ).grid(row=2, column=0, sticky="w", padx=12, pady=5)

            self.customer_combo = ctk.CTkComboBox(
                box,
                variable=self.customer_var,
                values=[],
                state="readonly",
                width=300
            )
            self.customer_combo.grid(
                row=2, column=1, columnspan=2,
                sticky="w", padx=6, pady=5
            )

            ctk.CTkLabel(
                box, text="Account type"
            ).grid(row=3, column=0, sticky="w", padx=12, pady=5)

            ctk.CTkComboBox(
                box,
                variable=self.type_var,
                values=list(config.ACCOUNT_TYPES),
                state="readonly",
                width=220
            ).grid(row=3, column=1, sticky="w", padx=6, pady=5)

            ctk.CTkLabel(
                box,
                text=f"Opening balance ({config.CURRENCY})"
            ).grid(row=4, column=0, sticky="w", padx=12, pady=5)

            ctk.CTkEntry(
                box,
                textvariable=self.opening_var,
                width=220,
                placeholder_text="0.00"
            ).grid(row=4, column=1, sticky="w", padx=6, pady=5)

            ctk.CTkButton(
                box,
                text="Open Account",
                command=self.open_account,
                height=36
            ).grid(row=5, column=0, padx=12, pady=12, sticky="w")

            self.open_msg = ctk.CTkLabel(
                box,
                text="",
                wraplength=520,
                justify="left"
            )
            self.open_msg.grid(
                row=5, column=1, columnspan=2,
                sticky="w", padx=6, pady=12
            )

        else:
            self.readonly_notice()

        # Search and filters
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(fill="x", padx=10, pady=(12, 6))

        ctk.CTkLabel(
            bar,
            text="Search accounts"
        ).pack(side="left", padx=(0, 6))

        search_entry = ctk.CTkEntry(
            bar,
            textvariable=self.search_var,
            width=230,
            placeholder_text="Account no., customer ID or name"
        )
        search_entry.pack(side="left", padx=4)
        search_entry.bind("<Return>", lambda _e: self.refresh())

        ctk.CTkLabel(
            bar, text="Status"
        ).pack(side="left", padx=(10, 4))

        ctk.CTkComboBox(
            bar,
            variable=self.filter_var,
            values=["All", "active", "frozen", "closed"],
            state="readonly",
            width=110
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            bar,
            text="Search",
            width=90,
            command=self.refresh
        ).pack(side="left", padx=6)

        # Account table
        self.table = DataTable(
            self,
            [
                ("Account No.", 110, "w"),
                ("Customer", 190, "w"),
                ("Customer ID", 100, "w"),
                ("Type", 100, "w"),
                ("Balance", 110, "e"),
                ("Status", 70, "w"),
                ("Opened (UTC)", 140, "w"),
            ],
            height=10,
            on_select=self._sync_buttons
        )
        self.table.pack(
            fill="both", expand=True, padx=10, pady=5
        )

        # Account actions
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(8, 10))

        self.btn_freeze = ctk.CTkButton(
            actions,
            text="Freeze",
            width=100,
            command=lambda: self.change_status("frozen")
        )

        self.btn_unfreeze = ctk.CTkButton(
            actions,
            text="Unfreeze",
            width=100,
            command=lambda: self.change_status("active")
        )

        self.btn_close = ctk.CTkButton(
            actions,
            text="Close Account",
            width=130,
            fg_color="#B91C1C",
            hover_color="#991B1B",
            command=lambda: self.change_status("closed")
        )

        if self.can("manage_accounts"):
            for button in (
                self.btn_freeze,
                self.btn_unfreeze,
                self.btn_close
            ):
                button.pack(side="left", padx=(0, 8))

        self.action_msg = ctk.CTkLabel(
            actions,
            text="",
            wraplength=500,
            justify="left"
        )
        self.action_msg.pack(side="left", padx=8)

        self.refresh()
        self._sync_buttons()

    def refresh(self, select_id=None):
        status = untr(self.filter_var.get())

        try:
            accounts = self.ctx.banking.search_accounts(
                self.user,
                self.search_var.get(),
                None if untr(status) == "All" else untr(status)
            )
        except Exception as exc:
            return self.fail(exc)

        self.table.set_rows(
            (
                a.id,
                (
                    a.account_number,
                    a.customer_name,
                    a.customer_number,
                    a.account_type,
                    format_money(a.balance),
                    a.status.title(),
                    a.opened_at
                )
            )
            for a in accounts
        )

        if select_id:
            self.table.select(select_id)

        self._sync_buttons()

    def _selected_account(self):
        iid = self.table.selected()

        if not iid:
            return None

        try:
            return self.ctx.banking.accounts.get(int(iid))
        except Exception:
            return None

    def _sync_buttons(self):
        acct = self._selected_account()
        status = acct.status if acct else None

        if not hasattr(self, "btn_freeze"):
            return

        self.btn_freeze.configure(
            state="normal" if status == "active" else "disabled"
        )

        self.btn_unfreeze.configure(
            state="normal" if status == "frozen" else "disabled"
        )

        self.btn_close.configure(
            state=(
                "normal"
                if status in ("active", "frozen")
                else "disabled"
            )
        )

    def find_customers(self):
        try:
            found = self.ctx.banking.search_customers(
                self.user,
                self.find_var.get()
            )
        except Exception as exc:
            return self.fail(exc)

        found = [c for c in found if c.is_active]

        self.customer_lookup = {
            f"{c.customer_number} - {c.full_name}": c.id
            for c in found
        }

        self.customer_combo.configure(
            values=list(self.customer_lookup)
        )

        if found:
            self.customer_var.set(
                next(iter(self.customer_lookup))
            )
            set_message(
                self.open_msg,
                f"{len(found)} active customer(s) found.",
                ok=True
            )
        else:
            self.customer_var.set("")
            set_message(
                self.open_msg,
                "No active customer matches that search.",
                ok=False
            )

    def open_account(self):
        customer_id = self.customer_lookup.get(
            self.customer_var.get()
        )

        if customer_id is None:
            set_message(
                self.open_msg,
                "Find and select a customer first.",
                ok=False
            )
            return

        try:
            opening = parse_money(
                self.opening_var.get(),
                "Opening balance"
            )

            account = self.ctx.banking.open_account(
                self.user,
                customer_id,
                untr(self.type_var.get()),
                opening
            )

        except BankError as exc:
            set_message(self.open_msg, str(exc), ok=False)
            return

        except Exception as exc:
            return self.fail(exc)

        set_message(
            self.open_msg,
            f"Account {account.account_number} opened "
            f"with balance {format_money(account.balance)}.",
            ok=True
        )

        self.opening_var.set("0.00")
        self.refresh(select_id=account.id)

    def change_status(self, new_status):
        acct = self._selected_account()

        if not acct:
            return

        if new_status == "closed":
            confirmed = messagebox.askyesno(
                "Close account",
                f"Close account {acct.account_number}? "
                "A closed account cannot be reopened.",
                parent=self
            )

            if not confirmed:
                return

        try:
            updated = self.ctx.banking.set_account_status(
                self.user,
                acct.id,
                new_status
            )

        except BankError as exc:
            set_message(self.action_msg, str(exc), ok=False)
            return

        except Exception as exc:
            return self.fail(exc)

        set_message(
            self.action_msg,
            f"Account {updated.account_number} "
            f"is now {updated.status}.",
            ok=True
        )

        self.refresh(select_id=updated.id)
