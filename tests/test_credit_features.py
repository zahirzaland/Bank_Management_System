import sqlite3
import tempfile
import os
import unittest
from datetime import datetime, timezone

from database import Database
from exceptions import (AccountStateError, DuplicateError, PermissionDenied, ValidationError)
from tests.helpers import BankTestCase


class KycTests(BankTestCase):
    def test_kyc_is_required_before_opening_account(self):
        customer = self.bank.create_customer(self.teller, {
            "full_name": "Pending Person", "phone": "555-0188"})
        with self.assertRaises(AccountStateError):
            self.bank.open_account(self.teller, customer.id, "Savings", 0)
        with self.assertRaises(PermissionDenied):
            self.bank.update_customer_kyc(self.viewer, customer.id, "verified")
        customer = self.bank.update_customer_kyc(self.admin, customer.id, "verified", "Reviewed")
        self.assertEqual(customer.kyc_status, "verified")
        self.assertTrue(customer.kyc_verified_at)
        account = self.bank.open_account(self.teller, customer.id, "Savings", 0)
        self.assertEqual(account.balance, 0)
        self.bank.update_customer_kyc(self.teller, customer.id, "pending")
        with self.assertRaises(AccountStateError):
            self.s.loans.apply(self.teller, customer.id, account.id, 1000, 0, 1)
        self.bank.update_customer_kyc(self.teller, customer.id, "verified")


class LoanTests(BankTestCase):
    def test_fixed_interest_loan_lifecycle_uses_transaction_ledger(self):
        account = self.make_account(opening=50_000)
        customer = self.bank.get_customer(self.teller, account.customer_id)
        loan = self.s.loans.apply(self.teller, customer.id, account.id, 100_000, 1200, 12, "Test request")
        self.assertEqual(loan.amount_due, 112_000)
        self.assertEqual(loan.status, "pending")
        with self.assertRaises(PermissionDenied):
            self.s.loans.decide(self.teller, loan.id, True)
        with self.assertRaises(PermissionDenied):
            self.s.loans.disburse(self.admin, loan.id)

        loan = self.s.loans.decide(self.admin, loan.id, True)
        self.assertEqual(loan.status, "approved")
        loan = self.s.loans.disburse(self.teller, loan.id)
        self.assertEqual(loan.status, "active")
        self.assertEqual(self.balance(account), 150_000)

        loan = self.s.loans.repay(self.teller, loan.id, 20_000)
        self.assertEqual(loan.paid, 20_000)
        loan = self.s.loans.repay(self.teller, loan.id, loan.outstanding)
        self.assertEqual(loan.status, "paid")
        self.assertEqual(loan.paid, loan.amount_due)
        self.assertEqual(self.balance(account), 38_000)
        self.assertTrue(self.s.reports.ledger_is_consistent())

    def test_loan_disbursement_and_repayments_appear_in_reports(self):
        account = self.make_account(opening=50_000)
        customer = self.bank.get_customer(self.teller, account.customer_id)
        loan = self.s.loans.apply(self.teller, customer.id, account.id, 100_000, 1200, 12)
        self.s.loans.decide(self.admin, loan.id, True)

        loan = self.s.loans.disburse(self.teller, loan.id)
        self.assertEqual(loan.status, "active")
        self.assertEqual(self.balance(account), 150_000)
        transactions = self.bank.search_transactions(
            self.teller, account_number=account.account_number)
        disbursement = next(tx for tx in transactions if "disbursement" in tx.note)
        self.assertEqual(disbursement.transaction_type, "deposit")
        self.assertEqual(disbursement.amount, 100_000)

        self.s.loans.repay(self.teller, loan.id, 20_000)
        self.s.loans.repay(self.teller, loan.id, 10_000)
        columns, rows = self.s.reports.generate(self.viewer, "Loan Repayments")
        self.assertEqual(len(rows), 2)
        self.assertIn("Loan Ref", columns)
        self.assertEqual({row[5] for row in rows}, {"200.00", "100.00"})
        self.assertTrue(all(row[2] == loan.loan_ref for row in rows))

        app_columns, app_rows = self.s.reports.generate(self.viewer, "Loan Applications")
        self.assertIn("Disbursed (UTC)", app_columns)
        self.assertEqual(len(app_rows), 1)
        self.assertEqual(app_rows[0][0], loan.loan_ref)

    def test_loan_requires_verified_customer_and_prevents_overpayment(self):
        account = self.make_account()
        customer = self.bank.get_customer(self.teller, account.customer_id)
        loan = self.s.loans.apply(self.teller, customer.id, account.id, 1000, 0, 1)
        self.s.loans.decide(self.admin, loan.id, True)
        self.s.loans.disburse(self.teller, loan.id)
        with self.assertRaises(ValidationError):
            self.s.loans.repay(self.teller, loan.id, 1001)

    def test_loan_rejection_is_terminal(self):
        account = self.make_account()
        customer = self.bank.get_customer(self.teller, account.customer_id)
        loan = self.s.loans.apply(self.teller, customer.id, account.id, 1000, 0, 1)
        self.s.loans.decide(self.admin, loan.id, False)
        with self.assertRaises(ValidationError):
            self.s.loans.disburse(self.teller, loan.id)


class InterestTests(BankTestCase):
    def test_monthly_interest_is_rounded_and_idempotent(self):
        account = self.make_account(opening=100_000, kind="Savings")
        period = datetime.now(timezone.utc).strftime("%Y-%m")
        preview = self.s.interest.preview(self.teller, account.id, period)
        self.assertEqual(preview["amount"], 167)
        self.assertFalse(preview["already_applied"])
        self.assertEqual(self.s.interest.apply(self.teller, account.id, period), 167)
        self.assertEqual(self.balance(account), 100_167)
        self.assertTrue(self.s.interest.preview(self.teller, account.id, period)["already_applied"])
        with self.assertRaises(DuplicateError):
            self.s.interest.apply(self.teller, account.id, period)
        self.assertTrue(self.s.reports.ledger_is_consistent())

    def test_interest_rejects_checking_invalid_month_and_viewer(self):
        checking = self.make_account(opening=100_000, kind="Checking")
        with self.assertRaises(AccountStateError):
            self.s.interest.preview(self.teller, checking.id, "2026-10")
        savings = self.make_account(
            customer=self.make_customer("Bob Jones", "555-0111"), opening=100_000)
        with self.assertRaises(ValidationError):
            self.s.interest.preview(self.teller, savings.id, "2026-13")
        with self.assertRaises(ValidationError):
            self.s.interest.preview(self.teller, savings.id, "1900-01")
        with self.assertRaises(PermissionDenied):
            self.s.interest.preview(self.viewer, savings.id, datetime.now(timezone.utc).strftime("%Y-%m"))


class CustomerKycMigrationTests(unittest.TestCase):
    def test_legacy_customer_rows_receive_pending_kyc(self):
        with tempfile.TemporaryDirectory() as temp:
            path = os.path.join(temp, "legacy.db")
            conn = sqlite3.connect(path)
            conn.execute("""CREATE TABLE customers (
                id INTEGER PRIMARY KEY, customer_number TEXT, full_name TEXT, phone TEXT,
                email TEXT, address TEXT, status TEXT, created_at TEXT, updated_at TEXT)""")
            conn.execute(
                "INSERT INTO customers VALUES (1, 'CUST-01', 'Legacy Person', '555-0100', NULL, NULL, 'active', 'now', 'now')")
            conn.commit()
            conn.close()

            db = Database(path)
            try:
                db.initialize()
                row = db.conn.execute("SELECT kyc_status, kyc_verified_at FROM customers WHERE id = 1").fetchone()
                self.assertEqual(row["kyc_status"], "pending")
                self.assertIsNone(row["kyc_verified_at"])
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
