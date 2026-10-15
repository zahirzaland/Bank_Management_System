import unittest

from tests.helpers import BankTestCase
from exceptions import (AccountStateError, InsufficientFundsError, PermissionDenied, ValidationError,
                        DuplicateError)
from utils import parse_money, format_money


class MoneyTests(unittest.TestCase):
    def test_parse_exact(self):
        self.assertEqual(parse_money("0.07"), 7)
        self.assertEqual(parse_money("1,234.50"), 123450)
        self.assertEqual(parse_money("$10"), 1000)
        self.assertEqual(parse_money("19.99"), 1999)

    def test_parse_rejects(self):
        for bad in ("", "abc", "-5", "1.234", "1e3", "1.2.3"):
            with self.assertRaises(ValidationError):
                parse_money(bad)

    def test_format(self):
        self.assertEqual(format_money(123456), "$1,234.56")
        self.assertEqual(format_money(5), "$0.05")


class DepositWithdrawTests(BankTestCase):
    def test_deposit_increases_balance_exactly(self):
        acct = self.make_account(opening=1000)
        self.bank.deposit(self.teller, acct.id, 2550, "cash")
        self.assertEqual(self.balance(acct), 3550)

    def test_withdraw_sufficient(self):
        acct = self.make_account(opening=5000)
        self.bank.withdraw(self.teller, acct.id, 5000)
        self.assertEqual(self.balance(acct), 0)

    def test_withdraw_insufficient_leaves_balance_and_history(self):
        acct = self.make_account(opening=1000)
        with self.assertRaises(InsufficientFundsError):
            self.bank.withdraw(self.teller, acct.id, 1001)
        self.assertEqual(self.balance(acct), 1000)
        self.assertEqual(len(self.bank.search_transactions(self.teller, transaction_type="withdrawal")), 0)

    def test_non_positive_and_invalid_amounts_rejected(self):
        acct = self.make_account(opening=1000)
        for amount in (0, -5, 1.5, "10", True, 10 ** 15):
            with self.assertRaises(ValidationError):
                self.bank.deposit(self.teller, acct.id, amount)
        self.assertEqual(self.balance(acct), 1000)

    def test_frozen_and_closed_accounts_reject_transactions(self):
        acct = self.make_account(opening=1000)
        self.bank.set_account_status(self.teller, acct.id, "frozen")
        with self.assertRaises(AccountStateError):
            self.bank.deposit(self.teller, acct.id, 100)
        with self.assertRaises(AccountStateError):
            self.bank.withdraw(self.teller, acct.id, 100)
        self.bank.set_account_status(self.teller, acct.id, "active")
        self.bank.withdraw(self.teller, acct.id, 1000)
        self.bank.set_account_status(self.teller, acct.id, "closed")
        with self.assertRaises(AccountStateError):
            self.bank.deposit(self.teller, acct.id, 100)

    def test_cannot_close_with_balance_or_reopen(self):
        acct = self.make_account(opening=100)
        with self.assertRaises(AccountStateError):
            self.bank.set_account_status(self.teller, acct.id, "closed")
        self.bank.withdraw(self.teller, acct.id, 100)
        self.bank.set_account_status(self.teller, acct.id, "closed")
        with self.assertRaises(AccountStateError):
            self.bank.set_account_status(self.teller, acct.id, "active")

    def test_note_is_validated(self):
        acct = self.make_account()
        with self.assertRaises(ValidationError):
            self.bank.deposit(self.teller, acct.id, 100, "x" * 201)


class TransferTests(BankTestCase):
    def test_transfer_moves_money(self):
        a, b = self.make_account(opening=5000), self.make_account(self.make_customer("Bob Jones", "555-0111"), 100)
        tx = self.bank.transfer(self.teller, a.id, b.id, 1200)
        self.assertEqual((self.balance(a), self.balance(b)), (3800, 1300))
        self.assertEqual(tx.source_account_number, a.account_number)
        self.assertEqual(tx.destination_account_number, b.account_number)

    def test_insufficient_transfer_changes_nothing(self):
        a, b = self.make_account(opening=500), self.make_account(self.make_customer("Bob Jones", "555-0111"), 100)
        before = len(self.bank.search_transactions(self.teller))
        with self.assertRaises(InsufficientFundsError):
            self.bank.transfer(self.teller, a.id, b.id, 501)
        self.assertEqual((self.balance(a), self.balance(b)), (500, 100))
        self.assertEqual(len(self.bank.search_transactions(self.teller)), before)

    def test_same_account_rejected(self):
        a = self.make_account(opening=500)
        with self.assertRaises(ValidationError):
            self.bank.transfer(self.teller, a.id, a.id, 100)

    def test_transfer_is_atomic_when_credit_step_fails(self):
        a, b = self.make_account(opening=5000), self.make_account(self.make_customer("Bob Jones", "555-0111"), 100)
        original = self.bank.accounts.adjust_balance
        calls = {"n": 0}

        def flaky(account_id, delta):
            calls["n"] += 1
            if calls["n"] == 2:  # debit succeeded, credit blows up
                raise RuntimeError("simulated crash")
            return original(account_id, delta)

        self.bank.accounts.adjust_balance = flaky
        before_tx = len(self.bank.search_transactions(self.teller))
        with self.assertRaises(RuntimeError):
            self.bank.transfer(self.teller, a.id, b.id, 1000)
        self.bank.accounts.adjust_balance = original
        self.assertEqual((self.balance(a), self.balance(b)), (5000, 100))
        self.assertEqual(len(self.bank.search_transactions(self.teller)), before_tx)
        self.assertFalse(self.db._depth)

    def test_transfer_to_frozen_account_rejected(self):
        a, b = self.make_account(opening=500), self.make_account(self.make_customer("Bob Jones", "555-0111"))
        self.bank.set_account_status(self.teller, b.id, "frozen")
        with self.assertRaises(AccountStateError):
            self.bank.transfer(self.teller, a.id, b.id, 100)
        self.assertEqual(self.balance(a), 500)


class ReversalTests(BankTestCase):
    def test_reverse_deposit(self):
        a = self.make_account(opening=1000)
        tx = self.bank.deposit(self.teller, a.id, 400)
        rev = self.bank.reverse_transaction(self.admin, tx.id, "entered in error")
        self.assertEqual(self.balance(a), 1000)
        self.assertEqual(rev.transaction_type, "reversal")
        self.assertEqual(self.bank.transactions.get(tx.id).status, "reversed")
        with self.assertRaises(ValidationError):
            self.bank.reverse_transaction(self.admin, tx.id, "again")
        with self.assertRaises(ValidationError):
            self.bank.reverse_transaction(self.admin, rev.id, "reverse the reversal")

    def test_reverse_transfer(self):
        a, b = self.make_account(opening=900), self.make_account(self.make_customer("Bob Jones", "555-0111"))
        tx = self.bank.transfer(self.teller, a.id, b.id, 300)
        self.bank.reverse_transaction(self.admin, tx.id, "wrong beneficiary")
        self.assertEqual((self.balance(a), self.balance(b)), (900, 0))

    def test_reversal_fails_if_money_already_gone(self):
        a = self.make_account()
        tx = self.bank.deposit(self.teller, a.id, 500)
        self.bank.withdraw(self.teller, a.id, 500)
        with self.assertRaises(InsufficientFundsError):
            self.bank.reverse_transaction(self.admin, tx.id, "too late")

    def test_only_admin_can_reverse(self):
        a = self.make_account()
        tx = self.bank.deposit(self.teller, a.id, 500)
        with self.assertRaises(PermissionDenied):
            self.bank.reverse_transaction(self.teller, tx.id, "nope")


class PermissionTests(BankTestCase):
    def test_viewer_is_read_only(self):
        acct = self.make_account(opening=100)
        with self.assertRaises(PermissionDenied):
            self.bank.deposit(self.viewer, acct.id, 100)
        with self.assertRaises(PermissionDenied):
            self.bank.create_customer(self.viewer, {"full_name": "Eve Adams", "phone": "555-0199"})
        self.assertTrue(self.bank.search_customers(self.viewer, ""))

    def test_admin_cannot_transact_or_edit_customers(self):
        acct = self.make_account(opening=100)
        with self.assertRaises(PermissionDenied):
            self.bank.withdraw(self.admin, acct.id, 10)

    def test_teller_cannot_manage_staff(self):
        with self.assertRaises(PermissionDenied):
            self.s.auth.create_user(self.teller, "x_user", "Passw0rd99", "teller")
        with self.assertRaises(PermissionDenied):
            self.s.reports.audit_entries(self.teller)

    def test_deactivated_user_loses_access(self):
        self.s.auth.set_active(self.admin, self.teller.id, False)
        stale = self.s.auth.staff.get(self.teller.id)
        with self.assertRaises(PermissionDenied):
            self.bank.search_customers(stale)


class CustomerAccountTests(BankTestCase):
    def test_validation(self):
        bad = [{"full_name": "", "phone": "555-0100"}, {"full_name": "A", "phone": "555-0100"},
               {"full_name": "Bob 123", "phone": "555-0100"}, {"full_name": "Bob Ray", "phone": "abc"},
               {"full_name": "Bob Ray", "phone": "555-0100", "email": "not-an-email"},
               {"full_name": "Bob Ray", "phone": "555-0100", "address": "x" * 300}]
        for data in bad:
            with self.assertRaises(ValidationError, msg=data):
                self.bank.create_customer(self.teller, data)

    def test_unique_customer_numbers_and_duplicate_detection(self):
        c1, c2 = self.make_customer(), self.make_customer("Bob Jones", "555-0111")
        self.assertNotEqual(c1.customer_number, c2.customer_number)
        with self.assertRaises(DuplicateError):
            self.make_customer()

    def test_account_numbers_unique(self):
        c = self.make_customer()
        numbers = {self.bank.open_account(self.teller, c.id, "Checking").account_number for _ in range(25)}
        self.assertEqual(len(numbers), 25)

    def test_opening_balance_creates_ledger_entry(self):
        acct = self.make_account(opening=7500)
        self.assertEqual(acct.balance, 7500)
        txs = self.bank.search_transactions(self.teller, account_number=acct.account_number)
        self.assertEqual([t.transaction_type for t in txs], ["opening"])

    def test_invalid_account_type_and_opening(self):
        c = self.make_customer()
        with self.assertRaises(ValidationError):
            self.bank.open_account(self.teller, c.id, "Platinum", 0)
        with self.assertRaises(ValidationError):
            self.bank.open_account(self.teller, c.id, "Savings", -1)

    def test_deactivate_requires_closed_accounts_and_keeps_record(self):
        c = self.make_customer()
        acct = self.bank.open_account(self.teller, c.id, "Savings", 0)
        with self.assertRaises(AccountStateError):
            self.bank.deactivate_customer(self.teller, c.id)
        self.bank.set_account_status(self.teller, acct.id, "closed")
        self.assertEqual(self.bank.deactivate_customer(self.teller, c.id).status, "inactive")
        with self.assertRaises(AccountStateError):
            self.bank.open_account(self.teller, c.id, "Savings", 0)
        self.assertEqual(self.bank.reactivate_customer(self.teller, c.id).status, "active")

    def test_search_by_id_name_and_account(self):
        c = self.make_customer("Maria Garcia", "555-0123")
        acct = self.bank.open_account(self.teller, c.id, "Savings", 0)
        self.make_customer("Bob Jones", "555-0111")
        for term in (c.customer_number, "garcia", acct.account_number):
            self.assertEqual([x.id for x in self.bank.search_customers(self.teller, term)], [c.id])

    def test_search_is_injection_and_wildcard_safe(self):
        self.make_customer()
        self.assertEqual(self.bank.search_customers(self.teller, "' OR 1=1 --"), [])
        self.assertEqual(self.bank.search_customers(self.teller, "%"), [])
        self.assertEqual(self.bank.search_transactions(self.teller, ref_or_id="1; DROP TABLE accounts"), [])


class HistoryAndLedgerTests(BankTestCase):
    def test_history_filters(self):
        a = self.make_account(opening=1000)
        self.bank.deposit(self.teller, a.id, 100)
        self.bank.withdraw(self.teller, a.id, 50)
        s = self.bank.search_transactions
        self.assertEqual(len(s(self.teller)), 3)
        self.assertEqual(len(s(self.teller, transaction_type="deposit")), 1)
        self.assertEqual(len(s(self.teller, account_number=a.account_number)), 3)
        self.assertEqual(len(s(self.teller, account_number="0000000000")), 0)
        ref = s(self.teller, transaction_type="withdrawal")[0]
        self.assertEqual([t.id for t in s(self.teller, ref_or_id=ref.ref)], [ref.id])
        self.assertEqual([t.id for t in s(self.teller, ref_or_id=str(ref.id))], [ref.id])
        self.assertEqual(len(s(self.teller, date_from="2000-01-01", date_to="2999-12-31")), 3)
        self.assertEqual(len(s(self.teller, date_from="2999-01-01")), 0)
        with self.assertRaises(ValidationError):
            s(self.teller, date_from="2030-01-02", date_to="2030-01-01")
        with self.assertRaises(ValidationError):
            s(self.teller, date_from="31/12/2030")

    def test_ledger_matches_balances_after_mixed_activity(self):
        a, b = self.make_account(opening=10000), self.make_account(self.make_customer("Bob Jones", "555-0111"), 500)
        self.bank.deposit(self.teller, a.id, 250)
        self.bank.withdraw(self.teller, b.id, 100)
        t = self.bank.transfer(self.teller, a.id, b.id, 3333)
        self.bank.reverse_transaction(self.admin, t.id, "test reversal")
        with self.assertRaises(InsufficientFundsError):
            self.bank.withdraw(self.teller, b.id, 10 ** 9)
        self.assertTrue(self.s.reports.ledger_is_consistent())

    def test_foreign_keys_enforced(self):
        self.assertEqual(self.db.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
