
"""Reports with CSV and PDF export (FR-15, FR-20, UC-07)."""

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from exceptions import BankError
from services.report_service import REPORT_TYPES
from utils import utc_today
from .widgets import BaseView, DataTable, set_message
from .i18n import tr, untr


class ReportView(BaseView):
    def __init__(self, parent, ctx):
        super().__init__(parent, ctx)
        self.configure(fg_color="#F7F8FC")

        self.columns = []
        self.rows = []

        self.title("Reports")

        today = utc_today()

        self.type_var = tk.StringVar(value=tr(REPORT_TYPES[0]))
        self.from_var = tk.StringVar(
            value=today.replace(day=1).isoformat()
        )
        self.to_var = tk.StringVar(value=today.isoformat())

        # Report controls
        bar = ctk.CTkFrame(
            self, fg_color="#F7F8FC"
        )
        bar.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            bar,
            text="Report",
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        self.report_combo = ctk.CTkComboBox(
            bar,
            variable=self.type_var,
            values=list(REPORT_TYPES),
            state="readonly",
            width=220,
        )
        self.report_combo.grid(
            row=1, column=0, padx=(0, 10), pady=(4, 0)
        )

        ctk.CTkLabel(
            bar,
            text="From (YYYY-MM-DD)",
        ).grid(row=0, column=1, sticky="w", padx=(0, 10))

        ctk.CTkEntry(
            bar,
            textvariable=self.from_var,
            width=140,
            placeholder_text="YYYY-MM-DD",
        ).grid(
            row=1, column=1, padx=(0, 10), pady=(4, 0)
        )

        ctk.CTkLabel(
            bar,
            text="To (YYYY-MM-DD)",
        ).grid(row=0, column=2, sticky="w", padx=(0, 10))

        ctk.CTkEntry(
            bar,
            textvariable=self.to_var,
            width=140,
            placeholder_text="YYYY-MM-DD",
        ).grid(
            row=1, column=2, padx=(0, 10), pady=(4, 0)
        )

        ctk.CTkButton(
            bar,
            text="Generate",
            command=self.generate,
            width=100,
        ).grid(
            row=1, column=3, padx=4, pady=(4, 0)
        )

        self.btn_export = ctk.CTkButton(
            bar,
            text="Export CSV...",
            command=self.export,
            width=120,
            state="disabled",
        )
        self.btn_export.grid(
            row=1, column=4, padx=4, pady=(4, 0)
        )

        self.btn_export_pdf = ctk.CTkButton(
            bar,
            text="Export PDF...",
            command=self.export_pdf,
            width=110,
            state="disabled",
        )
        self.btn_export_pdf.grid(
            row=1, column=5, padx=4, pady=(4, 0)
        )

        if not self.can("export"):
            self.btn_export.configure(state="disabled")
            self.btn_export_pdf.configure(state="disabled")

        # Help text
        ctk.CTkLabel(
            self,
            text=(
                "Leave a date empty for no limit. The Ledger Consistency "
                "Check and the current balances in Account Summary ignore "
                "dates. All times are UTC."
            ),
            text_color=("gray40", "gray70"),
            wraplength=860,
            justify="left",
        ).pack(
            anchor="w",
            pady=(6, 8),
        )

        # Report table
        self.table = DataTable(
            self,
            [("", 100, "w")],
            height=16,
        )
        self.table.pack(
            fill="both",
            expand=True,
        )

        # Status message
        self.message = ctk.CTkLabel(
            self,
            text="",
            anchor="w",
        )
        self.message.pack(
            anchor="w",
            fill="x",
            pady=(6, 0),
        )

        self.generate()

    def generate(self):
        try:
            cols, rows = self.ctx.reports.generate(
                self.user,
                untr(self.type_var.get()),
                self.from_var.get(),
                self.to_var.get(),
            )

        except BankError as exc:
            return set_message(
                self.message,
                str(exc),
                ok=False,
            )

        except Exception as exc:
            return self.fail(exc)

        self.columns = cols
        self.rows = rows

        if cols:
            width = max(110, min(260, 880 // len(cols)))
            widths = [width] * len(cols)

            self.table.set_columns([
                (
                    column,
                    column_width,
                    "e" if (
                        "(" in column
                        or column in (
                            "Count",
                            "Stored Balance",
                            "Ledger Balance",
                        )
                    ) else "w",
                )
                for column, column_width in zip(cols, widths)
            ])

            self.table.set_rows(
                (index, row)
                for index, row in enumerate(rows)
            )
        else:
            self.table.set_columns([("", 100, "w")])
            self.table.set_rows([])

        state = "normal" if self.can("export") and self.columns else "disabled"
        self.btn_export.configure(state=state)
        self.btn_export_pdf.configure(state=state)

        set_message(
            self.message,
            f"{len(rows)} row(s).",
            ok=True,
        )

    def export(self):
        if not self.columns:
            return

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export report",
            defaultextension=".csv",
            initialfile=(
                self.type_var.get().lower().replace(" ", "_") + ".csv"
            ),
            filetypes=[
                ("CSV files", "*.csv"),
            ],
        )

        if not path:
            return

        try:
            count = self.ctx.reports.export_csv(
                self.user,
                path,
                self.columns,
                self.rows,
                untr(self.type_var.get()),
            )

        except BankError as exc:
            return set_message(
                self.message,
                str(exc),
                ok=False,
            )

        except Exception as exc:
            return self.fail(exc)

        messagebox.showinfo(
            "Export complete",
            f"{count} row(s) exported to:\n{path}",
            parent=self,
        )

    def export_pdf(self):
        if not self.columns:
            return

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export report as PDF",
            defaultextension=".pdf",
            initialfile=(
                self.type_var.get().lower().replace(" ", "_") + ".pdf"
            ),
            filetypes=[("PDF files", "*.pdf")],
        )

        if not path:
            return

        try:
            count = self.ctx.reports.export_pdf(
                self.user,
                path,
                self.columns,
                self.rows,
                untr(self.type_var.get()),
            )

        except BankError as exc:
            return set_message(self.message, str(exc), ok=False)
        except Exception as exc:
            return self.fail(exc)

        messagebox.showinfo(
            "Export complete",
            f"{count} row(s) exported to PDF:\n{path}",
            parent=self,
        )
