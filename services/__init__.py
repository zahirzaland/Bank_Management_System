"""Service container: wires repositories and services around one Database."""
from dataclasses import dataclass, field
from typing import Callable, Optional

from models import StaffUser
from repositories import (AccountRepository, AuditRepository, CustomerRepository, LoanRepository, StaffRepository,
                          TransactionRepository)
from .auth_service import AuthService
from .backup_service import BackupService
from .banking_service import BankingService
from .interest_service import InterestService
from .loan_service import LoanService
from .report_service import ReportService


@dataclass
class Services:
    db: object
    auth: AuthService
    banking: BankingService
    reports: ReportService
    backup: BackupService
    loans: LoanService
    interest: InterestService
    user: Optional[StaffUser] = None                     # currently signed-in staff user
    request_logout: Optional[Callable[[], None]] = field(default=None, repr=False)


def build_services(db) -> Services:
    staff, customers, loans = StaffRepository(db), CustomerRepository(db), LoanRepository(db)
    accounts, transactions, audit = AccountRepository(db), TransactionRepository(db), AuditRepository(db)
    banking = BankingService(db, customers, accounts, transactions, audit)
    return Services(
        db=db,
        auth=AuthService(db, staff, audit),
        banking=banking,
        reports=ReportService(db, accounts, transactions, audit),
        backup=BackupService(db, audit),
        loans=LoanService(db, loans, banking, customers, accounts, audit),
        interest=InterestService(db, banking, accounts, audit),
    )
