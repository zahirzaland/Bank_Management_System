# Bank Management System (Educational Simulation)

Desktop prototype built from the SRS: **Python 3.11+ · CustomTkinter/ttk · SQLite**.
It simulates banking for learning/portfolio use. **It must not hold or move real funds or store real customer data.**

## Run

```bash
pip install -r requirements.txt      # enables PDF reports and Argon2 hashing
python main.py
```

* Tkinter must be installed (Windows/macOS Python installers include it; Debian/Ubuntu: `sudo apt install python3-tk`).
* First launch shows **First-time setup** to create the first administrator. There are no default passwords.
* Optional demo data (throw-away DB only): `python seed_demo.py` → logins `admin / Admin#2026`, `teller / Teller#2026`, `viewer / Viewer#2026`.
* Data lives in `data/bank.db`; errors are logged to `data/bms.log`. Override with `BMS_DB_PATH` / `BMS_DATA_DIR`.

## Roles

| Role | Can do |
|---|---|
| **admin** | View everything, review KYC, approve/reject and disburse loans, reports (CSV/PDF), audit log, manage staff, backup/restore, **reverse transactions** |
| **teller** | Create/update/deactivate customers, review KYC, apply for loans, open accounts, freeze/close, deposit, withdraw, transfer, disburse/repay loans, apply monthly interest, search, reports (CSV/PDF) |
| **viewer** | Read-only customers/accounts/transactions, reports (CSV/PDF) |

Routine deposits, withdrawals, and transfers are restricted to tellers (separation of duties). Administrators can review KYC, approve/reject loan applications, and disburse an approved loan through the dedicated loan workflow; this does not grant them access to routine transactions. Tellers can create applications, disburse and repay loans, and apply interest credits. The matrix is in `services/permissions.py`.

## KYC, loans and interest

* New customers start with **KYC pending**. A teller or administrator can record a pending, verified, or rejected review and internal notes in **Customers → Update KYC**. An account cannot be opened and a loan cannot be applied for until KYC is verified. This educational prototype does not store identity-document images or numbers.
* In **Loans**, staff can submit a request against one of the customer's active accounts, record a decision, disburse an approved loan to that account, and record full or partial repayments from it. Administrators and tellers can disburse approved loans; only tellers can record routine repayments. Interest is fixed and calculated upfront using simple interest: principal × APR × term in years, rounded to cents. It is an illustrative workflow, not an amortization schedule or real credit decision.
* **Reports** includes loan application balances, individual loan repayments, and monthly interest credits in addition to transaction and account reports. Date filters apply to each report's application, payment, or credit date.
* In **Interest**, tellers can preview and apply one monthly interest credit per account in the current UTC month. Savings earns 2.00% APR and Fixed Deposit earns 3.50% APR, calculated against the balance at the time of application. Checking accounts do not earn interest. Interest credits use the regular transaction ledger and cannot be applied twice for the same account/month.
* Signed-in users are automatically logged out after **15 minutes without keyboard or mouse activity**.
* The interface supports English and Pashto. Choose a language on the sign-in screen or dashboard; the choice is saved for the next launch. Stored account and transaction values remain language-neutral.

The UI uses `customtkinter` with Tkinter/ttk controls. SQLite, CSV, password hashing fallback (`scrypt`), and most supporting utilities come with Python. `argon2-cffi` is the recommended password hasher; `reportlab` provides PDF export.

## Architecture

```
main.py, config.py, utils.py, validation.py, exceptions.py, seed_demo.py
database/      connection.py (transactions, backup/restore), schema.sql
models/        dataclasses (Customer, Account, Transaction, StaffUser)
repositories/  parameterized SQL only (one class per table)
services/      auth, banking (all business rules), loans, interest, reports, backup, permissions, password hashing
ui/            CustomTkinter screens - no business rules; they call services; i18n.py translates interface text
tests/         unit tests, no GUI needed (NFR-08)
```

Key design points: money is **integer cents** (`utils.parse_money` uses `Decimal`, never float); every money movement runs in one `BEGIN IMMEDIATE` transaction with its ledger row and audit entry; foreign keys are enabled on the connection; the schema has CHECK constraints plus triggers that block deleting or editing completed transactions, customers, accounts, staff and audit rows. Corrections are made with **reversal records** (original is only flagged `reversed`). Timestamps are UTC.

## Tests

```bash
python -m unittest discover -s tests -t .
```

Covers deposits/withdrawals, atomic transfers (including a simulated mid-transfer crash), reversals, KYC gating, loan approval/disbursement/repayment, idempotent interest credits, permissions, validation, duplicate rejection, DB constraints/immutability, ledger-vs-balance consistency, login/lockout/hashing, last-admin protection, reports with date filters, CSV export (no secrets, formula-injection safe), backup/restore.

## Backup and restore (FR-19 / NFR-07)

* **Backup:** sign in as admin → **Staff → Backup & Restore → Create backup…** (uses SQLite's online backup; safe while open). Manual alternative: close the app and copy `data/bank.db`.
* **Restore:** same tab → **Restore from backup…**. The file is validated, a safety copy of the current DB is written to `data/backups/pre_restore_*.db`, data is replaced, and you are signed out. Manual alternative: close the app, replace `data/bank.db` with the backup.

## SRS traceability

| Requirement | Where |
|---|---|
| FR-01/02/03 login, hashing, logout | `services/auth_service.py`, `password_hasher.py`, `ui/login_view.py` |
| FR-04/05/06 customers | `banking_service.py`, `customer_repository.py`, `ui/customer_view.py` |
| FR-07/08 accounts, status | `banking_service.open_account / set_account_status`, `ui/account_view.py` |
| FR-09/10/11 deposit, withdraw, atomic transfer | `banking_service._move`, `ui/transaction_view.py` |
| FR-12 balance = ledger | `account_repository.ledger_rows`, report "Ledger Consistency Check" |
| FR-13/14 history, search | `transaction_repository.search`, History tab |
| FR-15/20 reports, CSV | `services/report_service.py`, `ui/report_view.py` |
| FR-16 audit | `audit_repository.py` (append-only), Staff → Audit Log |
| FR-17/18 validation, errors | `validation.py`, `utils.py`, `ui/errors.py` |
| FR-19 backup | `database/connection.py`, `backup_service.py` |
| Business rules 1-8 | `banking_service.py`, `schema.sql`, `permissions.py` |

## Design decisions beyond the SRS

* Deactivating a customer requires all accounts to be closed; closing an account requires a zero balance; closed accounts cannot be reopened.
* Duplicate customers (same name + phone) are rejected.
* Login lockout: 5 consecutive failures lock that username for 60 seconds (in memory, per session of the app).
* Loan interest is a fixed, upfront simple-interest estimate; monthly account interest is applied manually by a teller to the current balance. Neither is a production banking calculation.
* Passwords: ≥ 8 chars, letter + digit, ≤ 72 bytes.
* Without `argon2-cffi`/`bcrypt` the app uses `hashlib.scrypt` (standard KDF, random salt per password).

## Known limitations

Single-user desktop educational app with simplified loan and interest calculations; no KYC document verification, amortized lending, real payment rails, or real customer-data safeguards. The UI was verified here with a stubbed Tk layer plus the unit tests; please run `python main.py` once on your machine for a visual check.
