"""Business rules for customers, accounts and money movement.

Every money movement goes through ``_move`` inside one database transaction, so
the debit, the credit, the ledger record and the audit entry succeed or fail
together (FR-11, NFR-03). The service never imports Tkinter (NFR-08).
"""
from typing import List, Optional

import config
from exceptions import (AccountStateError, DuplicateError, InsufficientFundsError, NotFoundError,
                        ValidationError)
from models import Account, Customer, StaffUser, Transaction
from utils import day_bounds, format_money, parse_date, utc_now
from validation import clean_text, validate_customer
from .permissions import require


class BankingService:
    def __init__(self, db, customers, accounts, transactions, audit):
        self.db = db
        self.customers = customers
        self.accounts = accounts
        self.transactions = transactions
        self.audit = audit

    # ======================= customers =======================================
    def create_customer(self, actor: StaffUser, data: dict) -> Customer:
        require(actor, "manage_customers")
        fields = validate_customer(data)
        with self.db.transaction():
            if self.customers.find_duplicate(fields["full_name"], fields["phone"]):
                raise DuplicateError("A customer with the same name and phone number already exists.")
            customer = self.customers.create(**fields)
            self.audit.add(actor.id, "customer_created", "customer", customer.id, customer.customer_number)
        return customer

    def update_customer(self, actor: StaffUser, customer_id: int, data: dict) -> Customer:
        require(actor, "manage_customers")
        fields = validate_customer(data)
        with self.db.transaction():
            customer = self._customer(customer_id)
            if not customer.is_active:
                raise AccountStateError("Reactivate the customer before editing the record.")
            if self.customers.find_duplicate(fields["full_name"], fields["phone"], exclude_id=customer_id):
                raise DuplicateError("Another customer with the same name and phone number already exists.")
            self.customers.update(customer_id, **fields)
            changed = [k for k, v in fields.items() if getattr(customer, k) != v]
            self.audit.add(actor.id, "customer_updated", "customer", customer_id,
                           f"{customer.customer_number}; changed: {', '.join(changed) or 'nothing'}")
            return self.customers.get(customer_id)

    def update_customer_kyc(self, actor: StaffUser, customer_id: int, status: str, notes: str = "") -> Customer:
        require(actor, "manage_kyc")
        if status not in ("pending", "verified", "rejected"):
            raise ValidationError("Select a valid KYC status.")
        notes = clean_text(notes, "KYC notes", max_len=500)
        with self.db.transaction():
            customer = self._customer(customer_id)
            verified_at = utc_now() if status == "verified" else None
            self.customers.set_kyc(customer_id, status, notes or None, verified_at)
            self.audit.add(actor.id, "customer_kyc_updated", "customer", customer_id,
                           f"{customer.customer_number}: {customer.kyc_status} -> {status}")
            return self.customers.get(customer_id)

    def deactivate_customer(self, actor: StaffUser, customer_id: int) -> Customer:
        require(actor, "manage_customers")
        with self.db.transaction():
            customer = self._customer(customer_id)
            if self.customers.count_open_accounts(customer_id):
                raise AccountStateError("Close all of the customer's accounts before deactivating the customer.")
            self.customers.set_status(customer_id, "inactive")
            self.audit.add(actor.id, "customer_deactivated", "customer", customer_id, customer.customer_number)
            return self.customers.get(customer_id)

    def reactivate_customer(self, actor: StaffUser, customer_id: int) -> Customer:
        require(actor, "manage_customers")
        with self.db.transaction():
            customer = self._customer(customer_id)
            self.customers.set_status(customer_id, "active")
            self.audit.add(actor.id, "customer_reactivated", "customer", customer_id, customer.customer_number)
            return self.customers.get(customer_id)

    def search_customers(self, actor: StaffUser, term: str = "") -> List[Customer]:
        require(actor, "view")
        return self.customers.search(term)

    def get_customer(self, actor: StaffUser, customer_id: int) -> Customer:
        require(actor, "view")
        return self._customer(customer_id)

    def _customer(self, customer_id: int) -> Customer:
        customer = self.customers.get(customer_id)
        if not customer:
            raise NotFoundError("Customer not found.")
        return customer

    # ======================= accounts ========================================
    def open_account(self, actor: StaffUser, customer_id: int, account_type: str, opening_amount: int = 0) -> Account:
        require(actor, "manage_accounts")
        if account_type not in config.ACCOUNT_TYPES:
            raise ValidationError("Select a valid account type.")
        self._check_amount(opening_amount, allow_zero=True, field="Opening balance")
        with self.db.transaction():
            customer = self._customer(customer_id)
            if not customer.is_active:
                raise AccountStateError("Accounts can only be opened for active customers.")
            if customer.kyc_status != "verified":
                raise AccountStateError("Verify the customer's KYC before opening an account.")
            account = self.accounts.create(customer_id, account_type, config.CURRENCY)
            self.audit.add(actor.id, "account_opened", "account", account.id,
                           f"{account.account_number} ({account_type}) for {customer.customer_number}")
            if opening_amount > 0:
                self._move(actor, "opening", opening_amount, None, account.id, "Opening balance")
            return self.accounts.get(account.id)

    def set_account_status(self, actor: StaffUser, account_id: int, new_status: str) -> Account:
        require(actor, "manage_accounts")
        if new_status not in config.ACCOUNT_STATUSES:
            raise ValidationError("Invalid account status.")
        with self.db.transaction():
            account = self._account(account_id)
            if account.status == new_status:
                raise ValidationError(f"The account is already {new_status}.")
            if account.status == "closed":
                raise AccountStateError("A closed account cannot be reopened.")
            if new_status == "closed" and account.balance != 0:
                raise AccountStateError("An account can only be closed when its balance is zero.")
            self.accounts.set_status(account_id, new_status)
            self.audit.add(actor.id, "account_status_changed", "account", account_id,
                           f"{account.account_number}: {account.status} -> {new_status}")
            return self.accounts.get(account_id)

    def find_account(self, actor: StaffUser, account_number: str) -> Account:
        require(actor, "view")
        number = str(account_number or "").strip()
        if not number:
            raise ValidationError("Enter an account number.")
        account = self.accounts.get_by_number(number)
        if not account:
            raise NotFoundError(f"Account {number} was not found.")
        return account

    def list_customer_accounts(self, actor: StaffUser, customer_id: int) -> List[Account]:
        require(actor, "view")
        return self.accounts.list_for_customer(customer_id)

    def search_accounts(self, actor: StaffUser, term: str = "", status: Optional[str] = None) -> List[Account]:
        require(actor, "view")
        return self.accounts.search(term, status or None)

    def _account(self, account_id: int) -> Account:
        account = self.accounts.get(account_id)
        if not account:
            raise NotFoundError("Account not found.")
        return account

    # ======================= money movement ==================================
    def deposit(self, actor: StaffUser, account_id: int, amount: int, note: str = "") -> Transaction:
        require(actor, "transact")
        return self._move(actor, "deposit", amount, None, account_id, note)

    def withdraw(self, actor: StaffUser, account_id: int, amount: int, note: str = "") -> Transaction:
        require(actor, "transact")
        return self._move(actor, "withdrawal", amount, account_id, None, note)

    def transfer(self, actor: StaffUser, source_id: int, destination_id: int, amount: int, note: str = "") -> Transaction:
        require(actor, "transact")
        return self._move(actor, "transfer", amount, source_id, destination_id, note)

    def reverse_transaction(self, actor: StaffUser, transaction_id: int, reason: str) -> Transaction:
        """Post a compensating record; the original is flagged 'reversed', never edited or deleted."""
        require(actor, "reverse")
        reason = clean_text(reason, "Reason", required=True, min_len=3, max_len=120)
        with self.db.transaction():
            original = self.transactions.get(transaction_id)
            if not original:
                raise NotFoundError("Transaction not found.")
            if original.transaction_type == "reversal":
                raise ValidationError("A reversal cannot itself be reversed.")
            if original.status != "completed":
                raise ValidationError("This transaction has already been reversed.")
            reversal = self._move(actor, "reversal", original.amount, original.destination_account_id,
                                  original.source_account_id, f"Reversal of {original.ref}: {reason}",
                                  reversed_of_id=original.id)
            self.transactions.mark_reversed(original.id)
            self.audit.add(actor.id, "transaction_reversed", "transaction", original.id,
                           f"{original.ref} reversed by {reversal.ref}")
            return reversal

    def _check_amount(self, amount, *, allow_zero: bool = False, field: str = "Amount") -> None:
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ValidationError(f"{field} is invalid.")
        if amount < 0 or (amount == 0 and not allow_zero):
            raise ValidationError(f"{field} must be greater than zero.")
        if amount > config.MAX_AMOUNT_MINOR:
            raise ValidationError(f"{field} exceeds the maximum of {format_money(config.MAX_AMOUNT_MINOR)}.")

    def _usable(self, account_id: int) -> Account:
        account = self._account(account_id)
        if account.status != "active":
            raise AccountStateError(f"Account {account.account_number} is {account.status} and cannot be used for transactions.")
        return account

    def _move(self, actor: StaffUser, ttype: str, amount: int, source_id: Optional[int],
              destination_id: Optional[int], note: str, reversed_of_id: Optional[int] = None) -> Transaction:
        self._check_amount(amount)
        note = clean_text(note, "Note", max_len=200)
        with self.db.transaction():  # BEGIN IMMEDIATE: balances are read under the write lock
            source = self._usable(source_id) if source_id is not None else None
            destination = self._usable(destination_id) if destination_id is not None else None
            if source and destination:
                if source.id == destination.id:
                    raise ValidationError("Source and destination accounts must be different.")
                if source.currency != destination.currency:
                    raise ValidationError("Accounts use different currencies.")
            if source and source.balance < amount:
                raise InsufficientFundsError(
                    f"Insufficient funds. Available balance is {format_money(source.balance)}.")
            if source:
                self.accounts.adjust_balance(source.id, -amount)
            if destination:
                self.accounts.adjust_balance(destination.id, amount)
            currency = (source or destination).currency
            tx = self.transactions.insert(ttype, amount, currency, source_id, destination_id,
                                          actor.id, note, reversed_of_id)
            self.audit.add(actor.id, f"transaction_{ttype}", "transaction", tx.id,
                           f"{tx.ref} {format_money(amount)} from={tx.source_account_number or '-'} "
                           f"to={tx.destination_account_number or '-'}")
            return tx

    # ======================= history =========================================
    def search_transactions(self, actor: StaffUser, account_number: str = "", transaction_type: str = "",
                            date_from: str = "", date_to: str = "", ref_or_id: str = "") -> List[Transaction]:
        require(actor, "view")
        start, end = day_bounds(parse_date(date_from, "'From' date"), parse_date(date_to, "'To' date"))
        if transaction_type and transaction_type not in config.TRANSACTION_TYPES:
            raise ValidationError("Invalid transaction type filter.")
        return self.transactions.search(str(account_number or "").strip(), transaction_type, start, end,
                                        str(ref_or_id or "").strip())
