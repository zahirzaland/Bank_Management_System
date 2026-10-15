
"""Customer management (FR-04, FR-05, FR-06, UC-02)."""

import customtkinter as ctk
from tkinter import messagebox

from exceptions import BankError
from utils import format_money
from .widgets import BaseView, DataTable, add_field, set_message
from .i18n import tr, untr


class CustomerView(BaseView):
    def __init__(self, parent, ctx):
        super().__init__(parent, ctx)

        self.selected = None
        self.search_var = ctk.StringVar()
        self.vars = {
            k: ctk.StringVar()
            for k in (
                "number", "name", "phone",
                "email", "address", "status", "kyc"
            )
        }

        self.title("Customers")

        if not self.can("manage_customers"):
            self.readonly_notice()

        # Main content
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=5)

        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        # Left: Search and customer list
        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(
            row=0, column=0,
            sticky="nsew", padx=(0, 12)
        )

        bar = ctk.CTkFrame(left, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            bar,
            text="Search customers",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", pady=(0, 5))

        search_row = ctk.CTkFrame(
            bar, fg_color="transparent"
        )
        search_row.pack(fill="x")

        entry = ctk.CTkEntry(
            search_row,
            textvariable=self.search_var,
            placeholder_text="ID, name or account no.",
            height=35
        )
        entry.pack(
            side="left", fill="x", expand=True, padx=(0, 6)
        )
        entry.bind(
            "<Return>", lambda _e: self.refresh()
        )

        ctk.CTkButton(
            search_row,
            text="Search",
            width=85,
            height=35,
            command=self.refresh
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            search_row,
            text="Clear",
            width=65,
            height=35,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._clear_search
        ).pack(side="left")

        self.table = DataTable(
            left,
            [
                ("Customer ID", 105, "w"),
                ("Name", 190, "w"),
                ("Phone", 110, "w"),
                ("Email", 170, "w"),
                ("Status", 70, "w")
            ],
            height=16,
            on_select=self.on_select
        )
        self.table.pack(fill="both", expand=True)

        # Right: Customer form and accounts
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(
            row=0, column=1, sticky="nsew"
        )

        form = ctk.CTkFrame(
            right,
            corner_radius=10,
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E4E8F0",
        )
        form.pack(fill="x")

        form.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            form,
            text="Customer Details",
            font=ctk.CTkFont(size=17, weight="bold")
        ).grid(
            row=0, column=0, columnspan=2,
            sticky="w", padx=10, pady=(12, 8)
        )

        add_field(
            form, 1, "Customer ID",
            self.vars["number"], state="readonly"
        )
        add_field(
            form, 2, "Full name *",
            self.vars["name"]
        )
        add_field(
            form, 3, "Phone *",
            self.vars["phone"]
        )
        add_field(
            form, 4, "Email",
            self.vars["email"]
        )
        add_field(
            form, 5, "Address",
            self.vars["address"]
        )
        add_field(
            form, 6, "Status",
            self.vars["status"], state="readonly"
        )
        add_field(
            form, 7, "KYC status",
            self.vars["kyc"], state="readonly"
        )

        buttons = ctk.CTkFrame(
            form, fg_color="transparent"
        )
        buttons.grid(
            row=8, column=0, columnspan=2,
            sticky="w", padx=10, pady=(10, 0)
        )

        self.btn_save = ctk.CTkButton(
            buttons,
            text="Save New",
            width=100,
            command=self.save
        )

        self.btn_update = ctk.CTkButton(
            buttons,
            text="Update",
            width=85,
            command=self.update
        )

        self.btn_toggle = ctk.CTkButton(
            buttons,
            text="Deactivate",
            width=110,
            fg_color="#B45309",
            hover_color="#92400E",
            command=self.toggle_status
        )

        self.btn_cancel = ctk.CTkButton(
            buttons,
            text="Cancel",
            width=80,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self.clear_form
        )

        self.btn_kyc = ctk.CTkButton(
            form,
            text="Update KYC",
            width=100,
            fg_color="#475569",
            hover_color="#334155",
            command=self.update_kyc
        )
        self.btn_kyc.grid(row=9, column=0, sticky="w", padx=10, pady=(8, 0))

        for button in (
            self.btn_save,
            self.btn_update,
            self.btn_toggle,
            self.btn_cancel
        ):
            button.pack(side="left", padx=(0, 5))

        self.message = ctk.CTkLabel(
            form,
            text="",
            wraplength=330,
            justify="left",
            anchor="w"
        )
        self.message.grid(
            row=10, column=0, columnspan=2,
            sticky="w", padx=10, pady=(8, 12)
        )

        # Customer accounts
        acc = ctk.CTkFrame(
            right,
            corner_radius=10,
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E4E8F0",
        )
        acc.pack(fill="both", expand=True, pady=(10, 0))

        ctk.CTkLabel(
            acc,
            text="Accounts of Selected Customer",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=10, pady=(6, 2))

        self.acc_hint = ctk.CTkLabel(
            acc,
            text="Select a customer from the list to view their accounts.",
            anchor="w",
            justify="left",
            height=40,
            wraplength=480,
            font=ctk.CTkFont(size=11),
            text_color="#64748B",
        )
        self.acc_hint.pack(fill="x", padx=10, pady=(0, 8))

        self.acc_table = DataTable(
            acc,
            [
                ("Account No.", 100, "w"),
                ("Type", 90, "w"),
                ("Balance", 90, "e"),
                ("Status", 60, "w")
            ],
            height=6
        )
        self.acc_table.pack(
            fill="both", expand=True, padx=8, pady=(0, 8)
        )

        self.refresh()
        self._sync_buttons()

    # Data
    def _clear_search(self):
        self.search_var.set("")
        self.refresh()

    def refresh(self, select_id=None):
        try:
            customers = self.ctx.banking.search_customers(
                self.user,
                self.search_var.get()
            )
        except Exception as exc:
            return self.fail(exc)

        self.table.set_rows(
            (
                c.id,
                (
                    c.customer_number,
                    c.full_name,
                    c.phone,
                    c.email or "",
                    c.status.title()
                )
            )
            for c in customers
        )

        if select_id is not None:
            self.table.select(select_id)

    def on_select(self):
        iid = self.table.selected()

        if not iid:
            return

        try:
            customer = self.ctx.banking.get_customer(
                self.user, int(iid)
            )
            accounts = self.ctx.banking.list_customer_accounts(
                self.user, customer.id
            )
        except Exception as exc:
            return self.fail(exc)

        self.selected = customer

        self.vars["number"].set(customer.customer_number)
        self.vars["name"].set(customer.full_name)
        self.vars["phone"].set(customer.phone)
        self.vars["email"].set(customer.email or "")
        self.vars["address"].set(customer.address or "")
        self.vars["status"].set(customer.status.title())
        self.vars["kyc"].set(customer.kyc_status.title())

        self.acc_table.set_rows(
            (
                a.id,
                (
                    a.account_number,
                    a.account_type,
                    format_money(a.balance),
                    a.status.title()
                )
            )
            for a in accounts
        )
        self.acc_hint.configure(
            text=(
                f"{customer.full_name} · {len(accounts)} account(s)"
                if accounts
                else f"{customer.full_name} has no accounts yet."
            )
        )

        self.message.configure(text="")
        self._sync_buttons()

    def _form_data(self):
        return {
            "full_name": self.vars["name"].get(),
            "phone": self.vars["phone"].get(),
            "email": self.vars["email"].get(),
            "address": self.vars["address"].get()
        }

    def _sync_buttons(self):
        manage = self.can("manage_customers")
        manage_kyc = self.can("manage_kyc")
        has = self.selected is not None

        self.btn_save.configure(
            state="normal" if manage and not has else "disabled"
        )

        self.btn_update.configure(
            state=(
                "normal"
                if manage and has and self.selected.is_active
                else "disabled"
            )
        )

        self.btn_toggle.configure(
            state="normal" if manage and has else "disabled"
        )

        self.btn_toggle.configure(
            text=(
                "Deactivate"
                if not has or self.selected.is_active
                else "Reactivate"
            )
        )

        self.btn_cancel.configure(state="normal")
        self.btn_kyc.configure(state="normal" if manage_kyc and has else "disabled")

    def update_kyc(self):
        if not self.selected or not self.can("manage_kyc"):
            return

        customer = self.selected
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"{tr('Update KYC')} - {customer.full_name}")
        dialog.geometry("440x360")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="KYC verification",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(
            dialog,
            text="Record the review outcome. Do not enter real identity document numbers.",
            wraplength=390,
            justify="left",
            text_color="#64748B"
        ).pack(anchor="w", padx=20, pady=(0, 12))

        status_var = ctk.StringVar(value=tr(customer.kyc_status))
        ctk.CTkLabel(dialog, text="Review status").pack(anchor="w", padx=20)
        ctk.CTkComboBox(
            dialog, variable=status_var,
            values=["pending", "verified", "rejected"],
            state="readonly"
        ).pack(fill="x", padx=20, pady=(4, 12))

        ctk.CTkLabel(dialog, text="Review notes").pack(anchor="w", padx=20)
        notes = ctk.CTkTextbox(dialog, height=100)
        notes.pack(fill="both", expand=True, padx=20, pady=(4, 12))
        if customer.kyc_notes:
            notes.insert("1.0", customer.kyc_notes)

        def save():
            try:
                updated = self.ctx.banking.update_customer_kyc(
                    self.user, customer.id, untr(status_var.get()), notes.get("1.0", "end").strip())
            except BankError as exc:
                messagebox.showerror("KYC update", str(exc), parent=dialog)
                return
            except Exception as exc:
                self.fail(exc)
                return
            self.selected = updated
            self.vars["kyc"].set(updated.kyc_status.title())
            self.message.configure(text="KYC status updated.")
            dialog.destroy()

        ctk.CTkButton(dialog, text="Save KYC Status", command=save).pack(
            anchor="e", padx=20, pady=(0, 18))

    # Actions
    def clear_form(self):
        self.selected = None

        for var in self.vars.values():
            var.set("")

        self.table.clear_selection()
        self.acc_table.set_rows([])
        self.acc_hint.configure(
            text="Select a customer from the list to view their accounts."
        )
        self.message.configure(text="")

        self._sync_buttons()

    def _run(self, action, success_text):
        try:
            customer = action()

        except BankError as exc:
            set_message(self.message, str(exc), ok=False)
            return None

        except Exception as exc:
            self.fail(exc)
            return None

        self.selected = None
        self.refresh(select_id=customer.id)
        self.on_select()

        set_message(
            self.message,
            success_text.format(n=customer.customer_number),
            ok=True
        )

        return customer

    def save(self):
        self._run(
            lambda: self.ctx.banking.create_customer(
                self.user, self._form_data()
            ),
            "Customer {n} created."
        )

    def update(self):
        if self.selected:
            self._run(
                lambda: self.ctx.banking.update_customer(
                    self.user,
                    self.selected.id,
                    self._form_data()
                ),
                "Customer {n} updated."
            )

    def toggle_status(self):
        if not self.selected:
            return

        if self.selected.is_active:
            confirmed = messagebox.askyesno(
                "Deactivate customer",
                f"Deactivate {self.selected.full_name}?\n"
                "The record is kept for history.",
                parent=self
            )

            if not confirmed:
                return

            self._run(
                lambda: self.ctx.banking.deactivate_customer(
                    self.user, self.selected.id
                ),
                "Customer {n} deactivated."
            )

        else:
            self._run(
                lambda: self.ctx.banking.reactivate_customer(
                    self.user, self.selected.id
                ),
                "Customer {n} reactivated."
            )
