"""Date-filtered reports, ledger check and CSV export (FR-12, FR-15, FR-16, FR-20)."""
import csv
import re
from typing import List, Optional, Sequence, Tuple

import config
from exceptions import ValidationError
from utils import day_bounds, parse_date, plain_money
from .permissions import require

REPORT_TYPES = (
    "Transaction Summary",
    "Transaction Details",
    "Account Summary",
    "Ledger Consistency Check",
    "Loan Applications",
    "Loan Repayments",
    "Interest Credits",
)
_NUMERIC = re.compile(r"^-?[\d,]+(\.\d+)?$")


def _csv_safe(value) -> str:
    """Neutralise spreadsheet formula injection in exported text."""
    text = "" if value is None else str(value)
    if text and (text[0] in "=+@\t\r" or (text[0] == "-" and not _NUMERIC.match(text))):
        return "'" + text
    return text


class ReportService:
    def __init__(self, db, accounts, transactions, audit):
        self.db, self.accounts, self.transactions, self.audit = db, accounts, transactions, audit

    def generate(self, actor, report_type: str, date_from: str = "", date_to: str = "") -> Tuple[List[str], List[List[str]]]:
        require(actor, "reports")
        start, end = day_bounds(parse_date(date_from, "'From' date"), parse_date(date_to, "'To' date"))
        if report_type == "Transaction Summary":
            return self._transaction_summary(start, end)
        if report_type == "Transaction Details":
            return self._transaction_details(start, end)
        if report_type == "Account Summary":
            return self._account_summary(start, end)
        if report_type == "Ledger Consistency Check":
            return self._ledger_check()
        if report_type == "Loan Applications":
            return self._loan_applications(start, end)
        if report_type == "Loan Repayments":
            return self._loan_repayments(start, end)
        if report_type == "Interest Credits":
            return self._interest_credits(start, end)
        raise ValidationError("Select a report type.")

    @staticmethod
    def _range(column: str, start: Optional[str], end: Optional[str]):
        sql, params = "", []
        if start:
            sql += f" AND {column} >= ?"
            params.append(start)
        if end:
            sql += f" AND {column} < ?"
            params.append(end)
        return sql, params

    def _transaction_summary(self, start, end):
        clause, params = self._range("created_at", start, end)
        rows = self.db.conn.execute(
            f"""SELECT transaction_type, COUNT(*) AS n, COALESCE(SUM(amount_minor_units), 0) AS total
                FROM transactions WHERE 1 = 1{clause} GROUP BY transaction_type""", params).fetchall()
        by_type = {r["transaction_type"]: (r["n"], r["total"]) for r in rows}
        labels = [("deposit", "Deposits"), ("withdrawal", "Withdrawals"), ("transfer", "Transfers"),
                  ("opening", "Opening balances"), ("reversal", "Reversals")]
        out = [[label, str(by_type.get(key, (0, 0))[0]), plain_money(by_type.get(key, (0, 0))[1])]
               for key, label in labels]
        out.append(["All transactions", str(sum(n for n, _ in by_type.values())),
                    plain_money(sum(t for _, t in by_type.values()))])
        c_acc, p_acc = self._range("opened_at", start, end)
        c_cus, p_cus = self._range("created_at", start, end)
        out.append(["Accounts opened", str(self.db.conn.execute(
            f"SELECT COUNT(*) FROM accounts WHERE 1 = 1{c_acc}", p_acc).fetchone()[0]), "-"])
        out.append(["Customers registered", str(self.db.conn.execute(
            f"SELECT COUNT(*) FROM customers WHERE 1 = 1{c_cus}", p_cus).fetchone()[0]), "-"])
        return ["Metric", "Count", f"Total ({config.CURRENCY})"], out

    def _transaction_details(self, start, end):
        txs = self.transactions.search(start=start, end=end, limit=100_000)
        cols = ["Reference", "Date/Time (UTC)", "Type", f"Amount ({config.CURRENCY})", "From Account",
                "To Account", "Staff", "Status", "Note"]
        rows = [[t.ref, t.created_at, t.transaction_type, plain_money(t.amount), t.source_account_number or "",
                 t.destination_account_number or "", t.created_by_username, t.status, t.note or ""]
                for t in txs]
        return cols, rows

    def _account_summary(self, start, end):
        clause, params = self._range("opened_at", start, end)
        rows = self.db.conn.execute(
            f"""SELECT account_type, status, COUNT(*) AS n, COALESCE(SUM(balance_minor_units), 0) AS total
                FROM accounts WHERE 1 = 1{clause} GROUP BY account_type, status
                ORDER BY account_type, status""", params).fetchall()
        return (["Account Type", "Status", "Accounts (opened in range)", f"Current Balance ({config.CURRENCY})"],
                [[r["account_type"], r["status"], str(r["n"]), plain_money(r["total"])] for r in rows])

    def _ledger_check(self):
        rows = []
        for r in self.accounts.ledger_rows():
            ok = r["stored"] == r["ledger"]
            rows.append([r["account_number"], plain_money(r["stored"]), plain_money(r["ledger"]),
                         "OK" if ok else "MISMATCH"])
        return ["Account", "Stored Balance", "Ledger Balance", "Result"], rows

    def _loan_applications(self, start, end):
        clause, params = self._range("l.applied_at", start, end)
        rows = self.db.conn.execute(
            """SELECT l.loan_ref, c.full_name, a.account_number,
                      l.principal_minor_units, l.rate_basis_points, l.term_months,
                      l.amount_due_minor, l.paid_minor_units, l.status,
                      l.applied_at, l.disbursed_at, l.notes
               FROM loans l
               JOIN customers c ON c.id = l.customer_id
               JOIN accounts a ON a.id = l.account_id
               WHERE 1 = 1""" + clause + " ORDER BY l.applied_at DESC, l.id DESC", params
        ).fetchall()
        columns = ["Loan Ref", "Customer", "Account", f"Principal ({config.CURRENCY})",
                   "APR", "Months", f"Amount Due ({config.CURRENCY})", f"Paid ({config.CURRENCY})",
                   f"Outstanding ({config.CURRENCY})", "Status", "Application Date (UTC)",
                   "Disbursed (UTC)", "Notes"]
        data = [[r["loan_ref"], r["full_name"], r["account_number"],
                 plain_money(r["principal_minor_units"]),
                 f'{r["rate_basis_points"] / 100:.2f}%', str(r["term_months"]),
                 plain_money(r["amount_due_minor"]), plain_money(r["paid_minor_units"]),
                 plain_money(r["amount_due_minor"] - r["paid_minor_units"]),
                 r["status"], r["applied_at"], r["disbursed_at"] or "", r["notes"] or ""]
                for r in rows]
        return columns, data

    def _loan_repayments(self, start, end):
        clause, params = self._range("t.created_at", start, end)
        rows = self.db.conn.execute(
            """SELECT t.transaction_ref, t.created_at, l.loan_ref, c.full_name, a.account_number,
                      t.amount_minor_units, t.status, u.username, t.note
               FROM transactions t
               JOIN loans l ON t.note = 'Loan ' || l.loan_ref || ' repayment'
               JOIN customers c ON c.id = l.customer_id
               JOIN accounts a ON a.id = l.account_id
               JOIN staff_users u ON u.id = t.created_by
               WHERE t.transaction_type = 'withdrawal'""" + clause +
            " ORDER BY t.created_at DESC, t.id DESC", params
        ).fetchall()
        columns = ["Reference", "Date/Time (UTC)", "Loan Ref", "Customer", "Account",
                   f"Payment ({config.CURRENCY})", "Status", "Staff", "Details"]
        return columns, [[r["transaction_ref"], r["created_at"], r["loan_ref"], r["full_name"],
                          r["account_number"], plain_money(r["amount_minor_units"]),
                          r["status"], r["username"], r["note"]] for r in rows]

    def _interest_credits(self, start, end):
        clause, params = self._range("ia.applied_at", start, end)
        rows = self.db.conn.execute(
            """SELECT ia.period, ia.applied_at, c.full_name, a.account_number,
                      a.account_type, ia.rate_basis_points, ia.amount_minor_units,
                      t.transaction_ref, t.status
               FROM interest_applications ia
               JOIN accounts a ON a.id = ia.account_id
               JOIN customers c ON c.id = a.customer_id
               JOIN transactions t ON t.id = ia.transaction_id
               WHERE 1 = 1""" + clause + " ORDER BY ia.applied_at DESC, ia.id DESC", params
        ).fetchall()
        columns = ["Period", "Credit Date (UTC)", "Customer", "Account", "Account Type",
                   "APR", f"Credit ({config.CURRENCY})", "Reference", "Status"]
        return columns, [[r["period"], r["applied_at"], r["full_name"], r["account_number"],
                          r["account_type"], f'{r["rate_basis_points"] / 100:.2f}%',
                          plain_money(r["amount_minor_units"]), r["transaction_ref"], r["status"]]
                         for r in rows]

    def ledger_is_consistent(self) -> bool:
        return all(r["stored"] == r["ledger"] for r in self.accounts.ledger_rows())

    def audit_entries(self, actor, text: str = "") -> List[dict]:
        require(actor, "audit")
        return self.audit.list(text)

    def export_csv(self, actor, path, columns: Sequence[str], rows: Sequence[Sequence[str]], report_name: str = "report") -> int:
        require(actor, "export")
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:  # BOM so Excel reads UTF-8
            writer = csv.writer(handle)
            writer.writerow([_csv_safe(c) for c in columns])
            for row in rows:
                writer.writerow([_csv_safe(c) for c in row])
        with self.db.transaction():
            self.audit.add(actor.id, "report_exported", "report", None, f"{report_name}: {len(rows)} rows")
        return len(rows)

    def export_pdf(self, actor, path, columns: Sequence[str], rows: Sequence[Sequence[str]], report_name: str = "Report") -> int:
        """Export the current report as a paginated PDF and audit the export."""
        require(actor, "export")

        # Import lazily so CSV reports and the rest of the app work even before
        # the optional PDF dependency is installed.
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle
        from xml.sax.saxutils import escape

        page = landscape(A4)
        doc = SimpleDocTemplate(
            path,
            pagesize=page,
            leftMargin=12 * mm,
            rightMargin=12 * mm,
            topMargin=12 * mm,
            bottomMargin=12 * mm,
            title=report_name,
        )

        styles = getSampleStyleSheet()
        title_style = styles["Title"]
        title_style.alignment = TA_LEFT
        cell_style = ParagraphStyle(
            "ReportCell",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=8.5,
            spaceAfter=0,
        )
        header_style = ParagraphStyle(
            "ReportHeader",
            parent=cell_style,
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )

        safe = lambda value: escape("" if value is None else str(value)).replace("\n", "<br/>")
        table_data = [[Paragraph(safe(value), header_style) for value in columns]]
        table_data.extend(
            [Paragraph(safe(value), cell_style) for value in row]
            for row in rows
        )

        column_count = max(1, len(columns))
        available_width = page[0] - doc.leftMargin - doc.rightMargin
        table = LongTable(
            table_data,
            colWidths=[available_width / column_count] * column_count,
            repeatRows=1,
            hAlign="LEFT",
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ]))

        doc.build([
            Paragraph(safe(report_name), title_style),
            Spacer(1, 4 * mm),
            table,
        ])

        with self.db.transaction():
            self.audit.add(actor.id, "report_exported", "report", None, f"PDF {report_name}: {len(rows)} rows")
        return len(rows)
