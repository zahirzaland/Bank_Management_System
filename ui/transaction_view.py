
"""Deposits, withdrawals, transfers, history and search (FR-09 FR-14, UC-04 UC-06)."""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog

import config
from exceptions import BankError
from utils import format_money, parse_money
from .widgets import ERR_COLOR, MUTED_COLOR, BaseView, DataTable, add_field, set_message
from .i18n import tr, untr


class TransactionView(BaseView):
    def __init__(self, parent, ctx):
        super().__init__(parent, ctx)

        # Keep this module's canvas and tab surfaces consistently white.
        self.configure(fg_color="#F7F8FC")

        self.title("Transactions")

        # CustomTkinter tabs
        self.nb = ctk.CTkTabview(
            self,
            corner_radius=10,
            fg_color="#F7F8FC",
            segmented_button_fg_color="#F7F8FC",
            segmented_button_selected_color="#4F83F1",
            segmented_button_unselected_color="#F7F8FC",
            segmented_button_selected_hover_color="#3C70DA",
            segmented_button_unselected_hover_color="#F7F8FC",
        )
        self.nb.pack(fill="both", expand=True, padx=10, pady=5)

        if self.can("transact"):
            self.nb.add("Deposit / Withdraw")
            self.nb.add("Transfer")

            self.nb.tab("Deposit / Withdraw").configure(fg_color="#F7F8FC")
            self.nb.tab("Transfer").configure(fg_color="#F7F8FC")

            self._build_cash_tab(self.nb.tab("Deposit / Withdraw"))
            self._build_transfer_tab(self.nb.tab("Transfer"))
        else:
            self.readonly_notice(
                "Your role may view and search transactions "
                "but cannot create them."
            )

        self.nb.add("History & Search")
        self.nb.tab("History & Search").configure(fg_color="#F7F8FC")
        self._build_history_tab(self.nb.tab("History & Search"))

        self.search_history()

    # ---- helpers -----------------------------------------------------

    def _lookup(self, number_var, info_label):
        """Find an account and display its current information."""
        try:
            acct = self.ctx.banking.find_account(
                self.user, number_var.get()
            )
        except BankError as exc:
            info_label.configure(
                text=str(exc), text_color=ERR_COLOR
            )
            return None
        except Exception as exc:
            self.fail(exc)
            return None

        usable = acct.status == "active"

        info_label.configure(
            text=(
                f"{acct.customer_name} | {acct.account_type} | "
                f"Balance {format_money(acct.balance)} | "
                f"{acct.status.title()}"
                + (
                    ""
                    if usable
                    else " (not available for transactions)"
                )
            ),
            text_color=MUTED_COLOR if usable else ERR_COLOR
        )

        return acct

    # ---- deposit / withdrawal ---------------------------------------

    def _build_cash_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)

        self.cash_acct = ctk.StringVar()
        self.cash_amount = ctk.StringVar()
        self.cash_note = ctk.StringVar()
        self.cash_type = ctk.StringVar(value="deposit")

        add_field(
            tab, 0, "Account number",
            self.cash_acct, width=24
        )

        ctk.CTkButton(
            tab,
            text="Look up",
            width=100,
            command=lambda: self._lookup(
                self.cash_acct, self.cash_info
            )
        ).grid(row=0, column=2, padx=6, pady=5)

        self.cash_info = ctk.CTkLabel(
            tab, text="", wraplength=650, justify="left"
        )
        self.cash_info.grid(
            row=1, column=0, columnspan=3,
            sticky="w", padx=10, pady=(0, 8)
        )

        ctk.CTkLabel(
            tab, text="Transaction type"
        ).grid(
            row=2, column=0, sticky="w",
            padx=10, pady=5
        )

        kind = ctk.CTkFrame(tab, fg_color="transparent")
        kind.grid(row=2, column=1, sticky="w", padx=5)

        ctk.CTkRadioButton(
            kind,
            text="Deposit",
            variable=self.cash_type,
            value="deposit"
        ).pack(side="left", padx=(0, 18), pady=5)

        ctk.CTkRadioButton(
            kind,
            text="Withdrawal",
            variable=self.cash_type,
            value="withdrawal"
        ).pack(side="left", pady=5)

        amount = add_field(
            tab, 3, f"Amount ({config.CURRENCY})",
            self.cash_amount, width=24
        )

        add_field(
            tab, 4, "Note (optional)",
            self.cash_note, width=48
        )

        ctk.CTkButton(
            tab,
            text="Submit Transaction",
            height=36,
            command=self.submit_cash
        ).grid(
            row=5, column=0,
            padx=10, pady=(12, 5), sticky="w"
        )

        self.cash_result = ctk.CTkLabel(
            tab, text="", wraplength=650, justify="left"
        )
        self.cash_result.grid(
            row=6, column=0, columnspan=3,
            sticky="w", padx=10, pady=8
        )

        amount.bind(
            "<Return>", lambda _e: self.submit_cash()
        )

    def submit_cash(self):
        acct = self._lookup(
            self.cash_acct, self.cash_info
        )

        if acct is None:
            return set_message(
                self.cash_result,
                "Enter a valid account number.",
                ok=False
            )

        if acct.status != "active":
            return set_message(
                self.cash_result,
                "This account is not available for transactions.",
                ok=False
            )

        deposit = self.cash_type.get() == "deposit"

        try:
            amount = parse_money(self.cash_amount.get())

            if amount <= 0:
                return set_message(
                    self.cash_result,
                    "Amount must be greater than zero.",
                    ok=False
                )

            verb, prep = (
                ("Deposit", "to")
                if deposit
                else ("Withdraw", "from")
            )

            if not messagebox.askyesno(
                "Confirm transaction",
                f"{verb} {format_money(amount)} {prep} "
                f"account {acct.account_number}\n"
                f"({acct.customer_name})?",
                parent=self
            ):
                return

            action = (
                self.ctx.banking.deposit
                if deposit
                else self.ctx.banking.withdraw
            )

            tx = action(
                self.user,
                acct.id,
                amount,
                self.cash_note.get()
            )

        except BankError as exc:
            return set_message(
                self.cash_result, str(exc), ok=False
            )
        except Exception as exc:
            return self.fail(exc)

        fresh = self._lookup(
            self.cash_acct, self.cash_info
        )

        if fresh is None:
            return set_message(
                self.cash_result,
                f"{tx.transaction_type.title()} completed. "
                f"Reference {tx.ref}.",
                ok=True
            )

        set_message(
            self.cash_result,
            f"{tx.transaction_type.title()} completed. "
            f"Reference {tx.ref}. "
            f"New balance {format_money(fresh.balance)}.",
            ok=True
        )

        self.cash_amount.set("")
        self.cash_note.set("")
        self.search_history()

    # ---- transfer ----------------------------------------------------

    def _build_transfer_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)

        self.tr_src = ctk.StringVar()
        self.tr_dst = ctk.StringVar()
        self.tr_amount = ctk.StringVar()
        self.tr_note = ctk.StringVar()

        add_field(
            tab, 0, "From account",
            self.tr_src, width=24
        )

        ctk.CTkButton(
            tab,
            text="Look up",
            width=100,
            command=lambda: self._lookup(
                self.tr_src, self.tr_src_info
            )
        ).grid(row=0, column=2, padx=6, pady=5)

        self.tr_src_info = ctk.CTkLabel(
            tab, text="", wraplength=650, justify="left"
        )
        self.tr_src_info.grid(
            row=1, column=0, columnspan=3,
            sticky="w", padx=10, pady=(0, 8)
        )

        add_field(
            tab, 2, "To account",
            self.tr_dst, width=24
        )

        ctk.CTkButton(
            tab,
            text="Look up",
            width=100,
            command=lambda: self._lookup(
                self.tr_dst, self.tr_dst_info
            )
        ).grid(row=2, column=2, padx=6, pady=5)

        self.tr_dst_info = ctk.CTkLabel(
            tab, text="", wraplength=650, justify="left"
        )
        self.tr_dst_info.grid(
            row=3, column=0, columnspan=3,
            sticky="w", padx=10, pady=(0, 8)
        )

        amount = add_field(
            tab, 4, f"Amount ({config.CURRENCY})",
            self.tr_amount, width=24
        )

        add_field(
            tab, 5, "Note (optional)",
            self.tr_note, width=48
        )

        ctk.CTkButton(
            tab,
            text="Transfer",
            height=36,
            command=self.submit_transfer
        ).grid(
            row=6, column=0,
            padx=10, pady=(12, 5), sticky="w"
        )

        self.tr_result = ctk.CTkLabel(
            tab, text="", wraplength=650, justify="left"
        )
        self.tr_result.grid(
            row=7, column=0, columnspan=3,
            sticky="w", padx=10, pady=8
        )

        amount.bind(
            "<Return>", lambda _e: self.submit_transfer()
        )

    def submit_transfer(self):
        src = self._lookup(
            self.tr_src, self.tr_src_info
        )
        dst = self._lookup(
            self.tr_dst, self.tr_dst_info
        )

        if src is None or dst is None:
            return set_message(
                self.tr_result,
                "Enter valid source and destination account numbers.",
                ok=False
            )

        if src.status != "active" or dst.status != "active":
            return set_message(
                self.tr_result,
                "Both accounts must be active.",
                ok=False
            )

        if src.id == dst.id:
            return set_message(
                self.tr_result,
                "Source and destination accounts must be different.",
                ok=False
            )

        try:
            amount = parse_money(self.tr_amount.get())

            if amount <= 0:
                return set_message(
                    self.tr_result,
                    "Amount must be greater than zero.",
                    ok=False
                )

            if not messagebox.askyesno(
                "Confirm transfer",
                f"Transfer {format_money(amount)}\n"
                f"From {src.account_number} ({src.customer_name})\n"
                f"To {dst.account_number} ({dst.customer_name})?",
                parent=self
            ):
                return

            tx = self.ctx.banking.transfer(
                self.user,
                src.id,
                dst.id,
                amount,
                self.tr_note.get()
            )

        except BankError as exc:
            return set_message(
                self.tr_result, str(exc), ok=False
            )
        except Exception as exc:
            return self.fail(exc)

        self._lookup(self.tr_src, self.tr_src_info)
        self._lookup(self.tr_dst, self.tr_dst_info)

        set_message(
            self.tr_result,
            f"Transfer completed. Reference {tx.ref}.",
            ok=True
        )

        self.tr_amount.set("")
        self.tr_note.set("")
        self.search_history()

    # ---- history and search -----------------------------------------

    def _build_history_tab(self, tab):
        panel = ctk.CTkFrame(
            tab,
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#D1D5DB",
            corner_radius=6,
        )
        panel.pack(fill="both", expand=True, padx=5, pady=5)

        self.h_acct = ctk.StringVar()
        self.h_type = ctk.StringVar(value=tr("All"))
        self.h_from = ctk.StringVar()
        self.h_to = ctk.StringVar()
        self.h_ref = ctk.StringVar()

        bar = ctk.CTkFrame(panel, fg_color="transparent")
        bar.pack(fill="x", padx=5, pady=5)

        fields = [
            ("Account no.", self.h_acct, 130),
            ("From (YYYY-MM-DD)", self.h_from, 140),
            ("To (YYYY-MM-DD)", self.h_to, 140),
            ("Txn ID / ref", self.h_ref, 160)
        ]

        for col, (label, var, width) in enumerate(fields):
            ctk.CTkLabel(
                bar, text=label
            ).grid(
                row=0, column=col,
                sticky="w", padx=(0, 6), pady=(0, 4)
            )

            entry = ctk.CTkEntry(
                bar,
                textvariable=var,
                width=width,
                height=34
            )
            entry.grid(
                row=1, column=col,
                sticky="ew", padx=(0, 8), pady=(0, 8)
            )
            entry.bind(
                "<Return>", lambda _e: self.search_history()
            )

        col = len(fields)

        ctk.CTkLabel(
            bar, text="Type"
        ).grid(
            row=0, column=col,
            sticky="w", padx=(0, 6), pady=(0, 4)
        )

        ctk.CTkComboBox(
            bar,
            variable=self.h_type,
            values=["All", *config.TRANSACTION_TYPES],
            state="readonly",
            width=140,
            height=34
        ).grid(
            row=1, column=col,
            padx=(0, 8), pady=(0, 8)
        )

        ctk.CTkButton(
            bar,
            text="Search",
            width=85,
            height=34,
            command=self.search_history
        ).grid(
            row=1, column=col + 1,
            padx=2, pady=(0, 8)
        )

        ctk.CTkButton(
            bar,
            text="Reset",
            width=75,
            height=34,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self.reset_history
        ).grid(
            row=1, column=col + 2,
            padx=2, pady=(0, 8)
        )

        self.h_table = DataTable(
            panel,
            [
                ("ID", 45, "e"),
                ("Reference", 190, "w"),
                ("Date/Time (UTC)", 130, "w"),
                ("Type", 80, "w"),
                ("Amount", 100, "e"),
                ("From", 95, "w"),
                ("To", 95, "w"),
                ("Staff", 80, "w"),
                ("Status", 80, "w"),
                ("Note", 220, "w")
            ],
            height=14
        )
        self.h_table.pack(
            fill="both", expand=True, padx=5, pady=(5, 0)
        )

        foot = ctk.CTkFrame(
            panel, fg_color="transparent"
        )
        foot.pack(fill="x", padx=5, pady=8)

        self.h_msg = ctk.CTkLabel(
            foot, text="", anchor="w"
        )
        self.h_msg.pack(side="left", fill="x", expand=True)

        if self.can("reverse"):
            ctk.CTkButton(
                foot,
                text="Reverse Selected...",
                fg_color="#B45309",
                hover_color="#92400E",
                command=self.reverse_selected
            ).pack(side="right")

    def reset_history(self):
        for var in (
            self.h_acct,
            self.h_from,
            self.h_to,
            self.h_ref
        ):
            var.set("")

        self.h_type.set(tr("All"))
        self.search_history()

    def search_history(self):
        kind = untr(self.h_type.get())

        try:
            txs = self.ctx.banking.search_transactions(
                self.user,
                self.h_acct.get(),
                "" if kind == "All" else kind,
                self.h_from.get(),
                self.h_to.get(),
                self.h_ref.get()
            )

        except BankError as exc:
            return set_message(
                self.h_msg, str(exc), ok=False
            )
        except Exception as exc:
            return self.fail(exc)

        self.h_table.set_rows(
            (
                t.id,
                (
                    t.id,
                    t.ref,
                    t.created_at,
                    t.transaction_type.title(),
                    format_money(t.amount),
                    t.source_account_number or "-",
                    t.destination_account_number or "-",
                    t.created_by_username,
                    t.status.title(),
                    t.note or ""
                )
            )
            for t in txs
        )

        message = f"{len(txs)} transaction(s) shown"

        if len(txs) >= config.SEARCH_LIMIT:
            message += f" (limit {config.SEARCH_LIMIT})"
        else:
            message += "."

        set_message(self.h_msg, message, ok=True)

    # ---- reversal ----------------------------------------------------

    def reverse_selected(self):
        iid = self.h_table.selected()

        if not iid:
            return set_message(
                self.h_msg,
                "Select a transaction to reverse.",
                ok=False
            )

        reason = simpledialog.askstring(
            "Reverse transaction",
            "Reason for the reversal:",
            parent=self
        )

        if reason is None:
            return

        if not reason.strip():
            return set_message(
                self.h_msg,
                "A reversal reason is required.",
                ok=False
            )

        if not messagebox.askyesno(
            "Confirm reversal",
            "Post a reversal for the selected transaction? "
            "The original record is kept.",
            parent=self
        ):
            return

        try:
            rev = self.ctx.banking.reverse_transaction(
                self.user, int(iid), reason.strip()
            )

        except BankError as exc:
            return set_message(
                self.h_msg, str(exc), ok=False
            )
        except Exception as exc:
            return self.fail(exc)

        self.search_history()

        set_message(
            self.h_msg,
            f"Reversal posted: {rev.ref}.",
            ok=True
        )
