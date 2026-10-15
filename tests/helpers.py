"""Shared fixtures: an in-memory database wired with all services."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database  # noqa: E402
from services import build_services  # noqa: E402

ADMIN_PW = "Admin#Pass1"
TELLER_PW = "Teller#Pass1"
VIEWER_PW = "Viewer#Pass1"


class BankTestCase(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.db.initialize()
        self.s = build_services(self.db)
        self.admin = self.s.auth.bootstrap_admin("admin", ADMIN_PW)
        self.teller = self.s.auth.create_user(self.admin, "teller", TELLER_PW, "teller")
        self.viewer = self.s.auth.create_user(self.admin, "viewer", VIEWER_PW, "viewer")
        self.bank = self.s.banking

    def tearDown(self):
        self.db.close()

    def make_customer(self, name="Alice Smith", phone="555-0100"):
        customer = self.bank.create_customer(self.teller, {"full_name": name, "phone": phone})
        return self.bank.update_customer_kyc(self.teller, customer.id, "verified", "Test fixture verified")

    def make_account(self, customer=None, opening=0, kind="Savings"):
        customer = customer or self.make_customer()
        return self.bank.open_account(self.teller, customer.id, kind, opening)

    def balance(self, account):
        return self.bank.accounts.get(account.id).balance
