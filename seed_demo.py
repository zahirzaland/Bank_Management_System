"""Optional: load demo staff, customers, accounts and transactions (Phase 1 sample data).

Usage:  python seed_demo.py            (uses the configured database)
        BMS_DB_PATH=/tmp/demo.db python seed_demo.py

Demo logins are public knowledge - use this ONLY on a throw-away database.
"""
import sys

import config
from database import Database
from services import build_services
from utils import parse_money

DEMO_USERS = (("admin", "Admin#2026", "admin"), ("teller", "Teller#2026", "teller"),
              ("viewer", "Viewer#2026", "viewer"))
DEMO_CUSTOMERS = (("Amara Okafor", "555-0101", "amara@example.com", "12 Oak Street"),
                  ("Liam Chen", "555-0102", "liam@example.com", "48 River Road"),
                  ("Sofia Rossi", "555-0103", "sofia@example.com", "7 Hill Avenue"),
                  ("Noah Williams", "555-0104", None, None))


def main() -> int:
    db = Database(config.DB_PATH)
    db.initialize()
    s = build_services(db)
    if not s.auth.needs_bootstrap():
        print("The database already contains staff users; refusing to seed. Use a fresh database.")
        return 1
    admin = s.auth.bootstrap_admin(DEMO_USERS[0][0], DEMO_USERS[0][1])
    for name, password, role in DEMO_USERS[1:]:
        s.auth.create_user(admin, name, password, role)
    teller = s.auth.staff.get_by_username("teller")

    accounts = []
    for i, (name, phone, email, address) in enumerate(DEMO_CUSTOMERS):
        customer = s.banking.create_customer(teller, {"full_name": name, "phone": phone,
                                                      "email": email or "", "address": address or ""})
        customer = s.banking.update_customer_kyc(teller, customer.id, "verified", "Demo customer")
        savings = s.banking.open_account(teller, customer.id, "Savings", parse_money("1500.00") * (i + 1))
        checking = s.banking.open_account(teller, customer.id, "Checking", parse_money("250.00"))
        accounts += [savings, checking]
    s.banking.deposit(teller, accounts[1].id, parse_money("120.75"), "Paycheck")
    s.banking.withdraw(teller, accounts[0].id, parse_money("200"), "ATM withdrawal")
    s.banking.transfer(teller, accounts[2].id, accounts[0].id, parse_money("300"), "Rent share")
    s.banking.transfer(teller, accounts[4].id, accounts[3].id, parse_money("75.50"), "Dinner")
    print(f"Demo data loaded into {config.DB_PATH}")
    print("Logins (username / password / role):")
    for name, password, role in DEMO_USERS:
        print(f"  {name:<8} {password:<13} {role}")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
