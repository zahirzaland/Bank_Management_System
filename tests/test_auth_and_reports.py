import csv
import os
import tempfile
import unittest

import config
from tests.helpers import BankTestCase, ADMIN_PW, TELLER_PW
from exceptions import AuthenticationError, DuplicateError, ValidationError
from services import password_hasher
from services.report_service import REPORT_TYPES, _csv_safe


class AuthTests(BankTestCase):
    def test_login_success_and_audit(self):
        user = self.s.auth.login("admin", ADMIN_PW)
        self.assertEqual(user.role, "admin")
        self.assertIsNotNone(user.last_login_at)
        actions = [e["action"] for e in self.s.reports.audit_entries(self.admin)]
        self.assertIn("login_success", actions)

    def test_invalid_logins(self):
        for u, p in (("admin", "wrong"), ("nobody", ADMIN_PW), ("", ""), ("admin", "")):
            with self.assertRaises(AuthenticationError):
                self.s.auth.login(u, p)
        self.assertIn("login_failed", [e["action"] for e in self.s.reports.audit_entries(self.admin)])

    def test_generic_message_does_not_reveal_which_part_is_wrong(self):
        msgs = set()
        for u, p in (("admin", "wrong"), ("nobody", "wrongpass1")):
            try:
                self.s.auth.login(u, p)
            except AuthenticationError as exc:
                msgs.add(str(exc))
        self.assertEqual(len(msgs), 1)

    def test_lockout_after_repeated_failures(self):
        for _ in range(config.MAX_LOGIN_ATTEMPTS):
            with self.assertRaises(AuthenticationError):
                self.s.auth.login("teller", "bad-password1")
        with self.assertRaises(AuthenticationError) as ctx:
            self.s.auth.login("teller", TELLER_PW)  # correct password still blocked while locked
        self.assertIn("Too many", str(ctx.exception))

    def test_inactive_user_cannot_login(self):
        self.s.auth.set_active(self.admin, self.teller.id, False)
        with self.assertRaises(AuthenticationError):
            self.s.auth.login("teller", TELLER_PW)

    def test_passwords_are_hashed_not_stored(self):
        stored = self.db.conn.execute("SELECT password_hash FROM staff_users WHERE username='admin'").fetchone()[0]
        self.assertNotIn(ADMIN_PW, stored)
        self.assertTrue(password_hasher.verify_password(ADMIN_PW, stored))
        self.assertFalse(password_hasher.verify_password("other", stored))
        again = password_hasher.hash_password(ADMIN_PW)
        self.assertNotEqual(stored, again)  # salted

    def test_password_policy_and_username_rules(self):
        for pw in ("short1", "alllettersnodigit", "12345678901"):
            with self.assertRaises(ValidationError):
                self.s.auth.create_user(self.admin, "newuser", pw, "teller")
        with self.assertRaises(ValidationError):
            self.s.auth.create_user(self.admin, "bad name!", "Passw0rd99", "teller")
        with self.assertRaises(ValidationError):
            self.s.auth.create_user(self.admin, "newuser", "Passw0rd99", "superuser")
        with self.assertRaises(DuplicateError):
            self.s.auth.create_user(self.admin, "TELLER", "Passw0rd99", "teller")

    def test_last_admin_and_self_protection(self):
        with self.assertRaises(ValidationError):
            self.s.auth.set_active(self.admin, self.admin.id, False)
        with self.assertRaises(ValidationError):
            self.s.auth.change_role(self.admin, self.admin.id, "teller")
        second = self.s.auth.create_user(self.admin, "admin2", "Passw0rd99", "admin")
        self.s.auth.change_role(self.admin, second.id, "teller")  # allowed: another admin remains
        third = self.s.auth.create_user(self.admin, "admin3", "Passw0rd99", "admin")
        self.s.auth.set_active(third, self.admin.id, False)       # allowed: admin3 remains
        with self.assertRaises(ValidationError):
            self.s.auth.set_active(third, third.id, False)

    def test_bootstrap_only_once(self):
        with self.assertRaises(ValidationError):
            self.s.auth.bootstrap_admin("another", "Passw0rd99")

    def test_change_own_password(self):
        with self.assertRaises(AuthenticationError):
            self.s.auth.change_own_password(self.teller, "wrong", "NewPassw0rd1")
        self.s.auth.change_own_password(self.teller, TELLER_PW, "NewPassw0rd1")
        self.assertEqual(self.s.auth.login("teller", "NewPassw0rd1").username, "teller")

    def test_audit_never_contains_passwords(self):
        try:
            self.s.auth.login("admin", "SecretGuess123")
        except AuthenticationError:
            pass
        blob = " ".join(e["details"] for e in self.s.reports.audit_entries(self.admin))
        self.assertNotIn("SecretGuess123", blob)
        self.assertNotIn(ADMIN_PW, blob)


class ReportTests(BankTestCase):
    def setUp(self):
        super().setUp()
        self.a = self.make_account(opening=10000)
        self.b = self.make_account(self.make_customer("Bob Jones", "555-0111"))
        self.bank.deposit(self.teller, self.a.id, 500, "=HYPERLINK(\"http://evil\")")
        self.bank.withdraw(self.teller, self.a.id, 200)
        self.bank.transfer(self.teller, self.a.id, self.b.id, 1000)

    def test_summary_totals(self):
        cols, rows = self.s.reports.generate(self.viewer, "Transaction Summary")
        data = {r[0]: r for r in rows}
        self.assertEqual(data["Deposits"][1:], ["1", "5.00"])
        self.assertEqual(data["Withdrawals"][1:], ["1", "2.00"])
        self.assertEqual(data["Transfers"][1:], ["1", "10.00"])
        self.assertEqual(data["Opening balances"][1:], ["1", "100.00"])
        self.assertEqual(data["All transactions"][1], "4")
        self.assertEqual(data["Accounts opened"][1], "2")
        self.assertEqual(data["Customers registered"][1], "2")

    def test_date_filter_applies(self):
        _, rows = self.s.reports.generate(self.viewer, "Transaction Summary", "2999-01-01", "2999-12-31")
        self.assertEqual({r[0]: r[1] for r in rows}["All transactions"], "0")
        _, rows = self.s.reports.generate(self.viewer, "Transaction Details", "2000-01-01", "2999-12-31")
        self.assertEqual(len(rows), 4)
        with self.assertRaises(ValidationError):
            self.s.reports.generate(self.viewer, "Transaction Details", "2024-05-02", "2024-05-01")
        with self.assertRaises(ValidationError):
            self.s.reports.generate(self.viewer, "Transaction Details", "yesterday", "")

    def test_all_report_types_run_and_ledger_ok(self):
        for rtype in REPORT_TYPES:
            cols, rows = self.s.reports.generate(self.admin, rtype)
            self.assertTrue(cols)
            for row in rows:
                self.assertEqual(len(row), len(cols))
        _, rows = self.s.reports.generate(self.admin, "Ledger Consistency Check")
        self.assertTrue(all(r[3] == "OK" for r in rows))

    def test_csv_export_fields_and_injection_safety(self):
        cols, rows = self.s.reports.generate(self.teller, "Transaction Details")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.csv")
            self.s.reports.export_csv(self.teller, path, cols, rows, "Transaction Details")
            with open(path, encoding="utf-8-sig", newline="") as fh:
                raw = fh.read()
            with open(path, encoding="utf-8-sig", newline="") as fh:
                parsed = list(csv.reader(fh))
        self.assertEqual(parsed[0], cols)
        self.assertEqual(len(parsed), 1 + len(rows))
        self.assertNotIn("password", raw.lower())
        self.assertNotIn("scrypt$", raw)
        self.assertTrue(any(cell.startswith("'=HYPERLINK") for row in parsed for cell in row))
        self.assertIn("report_exported", [e["action"] for e in self.s.reports.audit_entries(self.admin)])

    def test_csv_safe_helper(self):
        self.assertEqual(_csv_safe("-5.00"), "-5.00")
        self.assertEqual(_csv_safe("-cmd"), "'-cmd")
        self.assertEqual(_csv_safe("@x"), "'@x")
        self.assertEqual(_csv_safe(None), "")


class AuditTests(BankTestCase):
    def test_significant_events_are_audited(self):
        c = self.make_customer()
        acct = self.bank.open_account(self.teller, c.id, "Savings", 100)
        self.bank.deposit(self.teller, acct.id, 50)
        self.bank.set_account_status(self.teller, acct.id, "frozen")
        actions = {e["action"] for e in self.s.reports.audit_entries(self.admin)}
        for expected in ("customer_created", "account_opened", "transaction_opening", "transaction_deposit",
                         "account_status_changed", "staff_created"):
            self.assertIn(expected, actions)

    def test_failed_operation_leaves_no_audit_trace_of_a_success(self):
        acct = self.make_account(opening=100)
        before = len(self.s.reports.audit_entries(self.admin))
        with self.assertRaises(ValidationError):
            self.bank.deposit(self.teller, acct.id, 0)
        self.assertEqual(len(self.s.reports.audit_entries(self.admin)), before)


if __name__ == "__main__":
    unittest.main()
