"""Loan applications, approval, disbursement and repayments."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import customtkinter as ctk

from exceptions import BankError
from utils import format_money, parse_money
from .widgets import BaseView, DataTable, set_message
from .i18n import get_language, tr


class LoanView(BaseView):
    def __init__(self, parent, ctx):
        super().__init__(parent, ctx)
        self.title("Loans")
        ctk.CTkLabel(
            self,
            text=("Select a pending loan to approve or reject it. Approved loans must then be "
                  "disbursed by a teller. Interest is estimated once from APR and term."),
            text_color="#64748B",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 8))

        form = ctk.CTkFrame(self, fg_color="#FFFFFF")
        form.pack(fill="x", padx=12, pady=4)
        form.grid_columnconfigure(1, weight=1)
        self.customer_values = {}
        self.account_values = {}
        customers = self.ctx.banking.search_customers(self.user)
        accounts = self.ctx.banking.search_accounts(self.user)
        self.customer_values = {
            f"{c.customer_number} | {c.full_name} [{tr(c.kyc_status)}]": c.id for c in customers
        }
        self.account_values = {
            f"{a.account_number} | {a.customer_name} [{tr(a.status)}]": a.id for a in accounts
        }
        self.customer_var = ctk.StringVar()
        self.account_var = ctk.StringVar()
        self.principal_var = ctk.StringVar()
        self.rate_var = ctk.StringVar(value="12")
        self.term_var = ctk.StringVar(value="12")
        self.note_var = ctk.StringVar()

        ctk.CTkLabel(form, text="Customer").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        ctk.CTkComboBox(form, variable=self.customer_var, values=list(self.customer_values),
                        state="readonly").grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        ctk.CTkLabel(form, text="Deposit account").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        ctk.CTkComboBox(form, variable=self.account_var, values=list(self.account_values),
                        state="readonly").grid(row=1, column=1, sticky="ew", padx=10, pady=5)

        fields = ctk.CTkFrame(form, fg_color="transparent")
        fields.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6)
        for col in range(4):
            fields.grid_columnconfigure(col, weight=1)
        for col, (label, variable, placeholder) in enumerate((
                ("Principal", self.principal_var, "1000.00"),
                ("APR (%)", self.rate_var, "12"),
                ("Term (months)", self.term_var, "12"),
                ("Notes", self.note_var, "Optional"))):
            ctk.CTkLabel(fields, text=label).grid(row=0, column=col, sticky="w", padx=4)
            ctk.CTkEntry(fields, textvariable=variable, placeholder_text=placeholder).grid(
                row=1, column=col, sticky="ew", padx=4, pady=(2, 6))

        self.create_button = ctk.CTkButton(form, text="Apply for Loan", command=self.apply)
        self.create_button.grid(row=3, column=0, sticky="w", padx=10, pady=(2, 10))
        self.message = ctk.CTkLabel(form, text="", anchor="w", wraplength=750)
        self.message.grid(row=3, column=1, sticky="w", padx=10, pady=(2, 10))

        self.table_wrap = ctk.CTkFrame(self, fg_color="transparent")
        self.table_wrap.pack(fill="both", expand=True, padx=12, pady=6)
        self.table = DataTable(self.table_wrap, [
            ("Loan Ref", 100, "w"), ("Customer", 145, "w"), ("Account", 100, "w"),
            ("Principal", 95, "e"), ("APR", 65, "e"), ("Months", 65, "e"),
            ("Amount Due", 100, "e"), ("Paid", 90, "e"), ("Status", 90, "w"),
        ], height=9)
        self.row_action_panel = ctk.CTkFrame(
            self.table_wrap, width=190, corner_radius=10, border_width=1,
            border_color=("gray80", "gray25"), fg_color=("#ffffff", "#1e1e1e"),
        )
        self.row_action_panel.pack_propagate(False)
        self.action_heading = ctk.CTkLabel(
            self.row_action_panel, text="Decision", height=38, anchor="center",
            fg_color=("#e9edf2", "#303030"), corner_radius=0,
        )
        self.action_heading.pack(fill="x")
        if get_language() == "ps":
            self.row_action_panel.pack(side="left", fill="y")
            self.table.pack(side="right", fill="both", expand=True)
        else:
            self.table.pack(side="left", fill="both", expand=True)
            self.row_action_panel.pack(side="right", fill="y")

        # The decision buttons live in their own fixed-width column beside the
        # status column. Their vertical positions follow the visible Treeview rows.
        self.row_action_widgets = {}
        self._row_action_states = {}
        self.table.tree.bind("<Configure>", lambda _event: self._schedule_row_actions())
        self.table.tree.bind("<Expose>", lambda _event: self._schedule_row_actions())
        self.table.tree.bind("<MouseWheel>", lambda _event: self._schedule_row_actions())
        self.table.tree.bind("<Button-4>", lambda _event: self._schedule_row_actions())
        self.table.tree.bind("<Button-5>", lambda _event: self._schedule_row_actions())
        self.table.tree.configure(yscrollcommand=self._on_table_y_scroll)
        self.table.ysb.configure(command=self._scroll_table_y)
        self.table.tree.configure(xscrollcommand=self._on_table_x_scroll)
        self.table.xsb.configure(command=self._scroll_table_x)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=12, pady=(2, 12))
        self.payment_var = ctk.StringVar()
        ctk.CTkEntry(actions, textvariable=self.payment_var, width=120, placeholder_text="Payment amount").pack(
            side="left", padx=(0, 6))
        self.repay_button = ctk.CTkButton(actions, text="Record Repayment", command=self.repay)
        self.repay_button.pack(side="left", padx=4)
        self.table.tree.bind("<<TreeviewSelect>>", lambda _event: self._sync_actions())
        self.refresh()

    def refresh(self):
        try:
            loans = self.ctx.loans.list_loans(self.user)
            self._row_action_states = {}
            for loan in loans:
                if loan.status == "pending" and self.can("approve_loans"):
                    self._row_action_states[loan.id] = "review"
                elif loan.status == "approved" and self.can("transact"):
                    self._row_action_states[loan.id] = "disburse"
                elif loan.status == "approved" and self.can("approve_loans"):
                    self._row_action_states[loan.id] = "teller_required"
            self.table.set_rows(
                (loan.id, (
                    loan.loan_ref, loan.customer_name, loan.account_number,
                    format_money(loan.principal), f"{loan.rate_basis_points / 100:.2f}%",
                    str(loan.term_months), format_money(loan.amount_due),
                    format_money(loan.paid), loan.status.title()))
                for loan in loans)
            self._sync_row_action_buttons()
            self._schedule_row_actions()
        except Exception as exc:
            self.fail(exc)
        self._sync_actions()

    def _sync_row_action_buttons(self):
        for loan_id in set(self.row_action_widgets) - set(self._row_action_states):
            for widget in self.row_action_widgets.pop(loan_id):
                widget.destroy()
        for loan_id, action in self._row_action_states.items():
            old = self.row_action_widgets.get(loan_id)
            if old:
                continue
            if action == "review":
                approve = ctk.CTkButton(
                    self.row_action_panel, text="Approve", width=82, height=28,
                    command=lambda selected_id=loan_id: self._decide_row(selected_id, True),
                )
                reject = ctk.CTkButton(
                    self.row_action_panel, text="Reject", width=82, height=28,
                    fg_color="#B54747", hover_color="#963A3A",
                    command=lambda selected_id=loan_id: self._decide_row(selected_id, False),
                )
                self.row_action_widgets[loan_id] = (approve, reject)
            elif action == "disburse":
                disburse = ctk.CTkButton(
                    self.row_action_panel, text="Disburse", width=166, height=28,
                    command=lambda selected_id=loan_id: self._disburse_row(selected_id),
                )
                self.row_action_widgets[loan_id] = (disburse,)
            else:
                waiting = ctk.CTkLabel(
                    self.row_action_panel, text="Teller disbursement required",
                    width=176, height=30, wraplength=165, justify="center",
                )
                self.row_action_widgets[loan_id] = (waiting,)

    def _decide_row(self, loan_id, approved):
        self.table.select(loan_id)
        self.decide(approved)

    def _disburse_row(self, loan_id):
        self.table.select(loan_id)
        self.disburse()

    def _schedule_row_actions(self):
        if self.winfo_exists():
            self.after_idle(self._place_row_action_buttons)

    def _place_row_action_buttons(self):
        tree = self.table.tree
        for loan_id, widgets in self.row_action_widgets.items():
            box = tree.bbox(str(loan_id), "#1")
            if not box:
                for widget in widgets:
                    widget.place_forget()
                continue
            row_y = tree.winfo_y() + box[1] + max(0, (box[3] - 28) // 2)
            if len(widgets) == 2:
                x_positions = (98, 8) if get_language() == "ps" else (8, 98)
            else:
                x_positions = (12,)
            for widget, x in zip(widgets, x_positions):
                widget.place(x=x, y=row_y)

    def _on_table_y_scroll(self, first, last):
        self.table.ysb.set(first, last)
        self._schedule_row_actions()

    def _on_table_x_scroll(self, first, last):
        self.table.xsb.set(first, last)
        self._schedule_row_actions()

    def _scroll_table_y(self, *args):
        self.table.tree.yview(*args)
        self._schedule_row_actions()

    def _scroll_table_x(self, *args):
        self.table.tree.xview(*args)
        self._schedule_row_actions()

    def _selected_loan(self):
        selected = self.table.selected()
        if not selected:
            return None
        return next((loan for loan in self.ctx.loans.list_loans(self.user) if loan.id == int(selected)), None)

    def _sync_actions(self):
        loan = self._selected_loan()
        self.repay_button.configure(
            state="normal" if loan and loan.status == "active" and self.can("transact") else "disabled")

    def _report(self, operation):
        try:
            operation()
            set_message(self.message, "Loan record updated.")
            self.refresh()
        except BankError as exc:
            set_message(self.message, str(exc), ok=False)
        except Exception as exc:
            self.fail(exc)

    def apply(self):
        try:
            customer_id = self.customer_values[self.customer_var.get()]
            account_id = self.account_values[self.account_var.get()]
            principal = parse_money(self.principal_var.get())
            rate_percent = Decimal(self.rate_var.get().strip())
            if not rate_percent.is_finite() or rate_percent < 0:
                raise ValueError
            rate_bps = int((rate_percent * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            term = int(self.term_var.get())
            loan = self.ctx.loans.apply(
                self.user, customer_id, account_id, principal, rate_bps, term, self.note_var.get())
            set_message(self.message, f"Application {loan.loan_ref} created; total due {format_money(loan.amount_due)}.")
            self.refresh()
        except (KeyError, InvalidOperation, ValueError):
            set_message(self.message, "Select a customer and account and enter valid amount, APR, and term.", ok=False)
        except BankError as exc:
            set_message(self.message, str(exc), ok=False)
        except Exception as exc:
            self.fail(exc)

    def decide(self, approved):
        loan = self._selected_loan()
        if loan:
            self._report(lambda: self.ctx.loans.decide(self.user, loan.id, approved))

    def disburse(self):
        loan = self._selected_loan()
        if loan:
            self._report(lambda: self.ctx.loans.disburse(self.user, loan.id))

    def repay(self):
        loan = self._selected_loan()
        if not loan:
            return
        try:
            amount = parse_money(self.payment_var.get())
        except BankError as exc:
            set_message(self.message, str(exc), ok=False)
            return
        self._report(lambda: self.ctx.loans.repay(self.user, loan.id, amount))
