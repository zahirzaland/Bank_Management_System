import os
import sqlite3
import tempfile
import unittest

from tests.helpers import BankTestCase
from exceptions import ValidationError


class ConstraintTests(BankTestCase):
    def test_duplicate_identifiers_rejected_by_database(self):
        c = self.make_customer()
        acct = self.make_account(c)
        conn = self.db.conn
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO customers (customer_number, full_name, phone, created_at, updated_at) "
                         "VALUES (?, 'X Y', '5550000', 'now', 'now')", (c.customer_number,))
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, currency, opened_at) "
                         "VALUES (?, ?, 'Savings', 'USD', 'now')", (acct.account_number, c.id))
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO staff_users (username, password_hash, role, created_at) "
                         "VALUES ('ADMIN', 'x', 'admin', 'now')")  # case-insensitive unique

    def test_negative_balance_blocked_by_database(self):
        acct = self.make_account(opening=100)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.conn.execute("UPDATE accounts SET balance_minor_units = -1 WHERE id = ?", (acct.id,))

    def test_bad_transaction_shapes_blocked(self):
        acct = self.make_account(opening=100)
        ins = ("INSERT INTO transactions (transaction_ref, transaction_type, amount_minor_units, currency, "
               "source_account_id, destination_account_id, created_by, created_at) VALUES (?, 'transfer', ?, 'USD', ?, ?, 1, 'now')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.conn.execute(ins, ("R1", 0, acct.id, None))      # zero amount
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.conn.execute(ins, ("R2", 5, acct.id, acct.id))   # same account
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.conn.execute(ins, ("R3", 5, None, None))         # no accounts

    def test_history_is_immutable(self):
        acct = self.make_account(opening=100)
        tx = self.bank.deposit(self.teller, acct.id, 50)
        conn = self.db.conn
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute("UPDATE transactions SET amount_minor_units = 1 WHERE id = ?", (tx.id,))
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM transactions WHERE id = ?", (tx.id,))
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM customers")
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM accounts")
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute("UPDATE audit_logs SET action = 'x'")
        with self.assertRaises(sqlite3.DatabaseError):
            conn.execute("DELETE FROM audit_logs")

    def test_foreign_key_violation(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.conn.execute("INSERT INTO accounts (account_number, customer_id, account_type, currency, opened_at) "
                                 "VALUES ('9999999999', 999, 'Savings', 'USD', 'now')")


class TransactionBlockTests(BankTestCase):
    def test_rollback_on_error_and_nesting(self):
        c = self.make_customer()
        with self.assertRaises(RuntimeError):
            with self.db.transaction():
                with self.db.transaction():
                    self.bank.customers.create("Temp Person", "5551234", None, None)
                raise RuntimeError("boom")
        self.assertIsNone(self.bank.customers.find_duplicate("Temp Person", "5551234"))
        self.assertIsNotNone(self.bank.customers.get(c.id))


class BackupRestoreTests(BankTestCase):
    def test_backup_and_restore_roundtrip(self):
        acct = self.make_account(opening=1234)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "backup.db")
            self.s.backup.create_backup(self.admin, path)
            self.bank.deposit(self.teller, acct.id, 9999)
            self.assertEqual(self.balance(acct), 11233)
            self.s.backup.restore_backup(self.admin, path)
            self.assertEqual(self.balance(acct), 1234)
            self.assertEqual(self.db.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertTrue(self.s.reports.ledger_is_consistent())

    def test_restore_rejects_foreign_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            junk = os.path.join(tmp, "junk.db")
            with open(junk, "wb") as fh:
                fh.write(b"this is not a database at all" * 10)
            other = os.path.join(tmp, "other.db")
            conn = sqlite3.connect(other)
            conn.execute("CREATE TABLE t (x)")
            conn.close()
            for path in (junk, other, os.path.join(tmp, "missing.db")):
                with self.assertRaises(ValidationError):
                    self.s.backup.restore_backup(self.admin, path)


if __name__ == "__main__":
    unittest.main()
