"""Monthly interest preview and crediting screen."""
from datetime import datetime, timezone

import customtkinter as ctk

from exceptions import BankError
from utils import format_money
from .widgets import BaseView, DataTable, set_message
from .i18n import tr


class InterestView(BaseView):
    def __init__(self, parent, ctx):
        super().__init__(parent, ctx)
        self.title("Monthly Interest")
        ctk.CTkLabel(
            self,
            text="Illustrative monthly simple interest: credited once per account and month.",
            text_color="#64748B",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 12))

        panel = ctk.CTkFrame(self,fg_color="#FFFFFF")
        panel.pack(fill="x", padx=12, pady=5)
        panel.grid_columnconfigure(1, weight=1)
        accounts = self.ctx.banking.search_accounts(self.user)
        self.account_values = {
            f"{a.account_number} | {a.customer_name} | {tr(a.account_type)}": a.id for a in accounts
        }
        self.account_var = ctk.StringVar()
        self.period_var = ctk.StringVar(value=datetime.now(timezone.utc).strftime("%Y-%m"))

        ctk.CTkLabel(panel, text="Account").grid(row=0, column=0, sticky="w", padx=12, pady=8)
        ctk.CTkComboBox(panel, variable=self.account_var, values=list(self.account_values),
                        state="readonly").grid(row=0, column=1, sticky="ew", padx=12, pady=8)
        ctk.CTkLabel(panel, text="Period (YYYY-MM)").grid(row=1, column=0, sticky="w", padx=12, pady=8)
        ctk.CTkEntry(panel, textvariable=self.period_var, width=130).grid(
            row=1, column=1, sticky="w", padx=12, pady=8)

        self.preview_label = ctk.CTkLabel(panel, text="Preview interest before applying.", anchor="w")
        self.preview_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=8)
        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.grid(row=3, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8))
        ctk.CTkButton(buttons, text="Preview", command=self.preview).pack(side="left", padx=4)
        ctk.CTkButton(buttons, text="Apply Interest", command=self.apply).pack(side="left", padx=4)
        self.message = ctk.CTkLabel(panel, text="", anchor="w")
        self.message.grid(row=4, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 8))

        self.table = DataTable(self, [
            ("Period", 120, "w"), ("Annual Rate", 120, "e"),
            ("Interest Credit", 150, "e"), ("Applied (UTC)", 180, "w"),
        ], height=10)
        self.table.pack(fill="both", expand=True, padx=12, pady=8)
        self._load_history()

    def _account_id(self):
        return self.account_values[self.account_var.get()]

    def preview(self):
        try:
            result = self.ctx.interest.preview(self.user, self._account_id(), self.period_var.get().strip())
            state = "already applied" if result["already_applied"] else "not yet applied"
            self.preview_label.configure(
                text=f"Monthly credit: {format_money(result['amount'])} "
                     f"({result['rate_basis_points'] / 100:.2f}% APR); {state}.")
            set_message(self.message, "")
        except KeyError:
            set_message(self.message, "Select an account.", ok=False)
        except BankError as exc:
            set_message(self.message, str(exc), ok=False)
        except Exception as exc:
            self.fail(exc)

    def apply(self):
        try:
            amount = self.ctx.interest.apply(self.user, self._account_id(), self.period_var.get().strip())
            set_message(self.message, f"Interest of {format_money(amount)} credited.")
            self.preview()
            self._load_history()
        except KeyError:
            set_message(self.message, "Select an account.", ok=False)
        except BankError as exc:
            set_message(self.message, str(exc), ok=False)
        except Exception as exc:
            self.fail(exc)

    def _load_history(self):
        try:
            account_id = self._account_id()
        except KeyError:
            self.table.set_rows([])
            return
        try:
            rows = self.ctx.interest.history(self.user, account_id)
            self.table.set_rows(
                (index, (row["period"], f"{row['rate_basis_points'] / 100:.2f}%",
                         format_money(row["amount_minor_units"]), row["applied_at"]))
                for index, row in enumerate(rows))
        except Exception as exc:
            self.fail(exc)
