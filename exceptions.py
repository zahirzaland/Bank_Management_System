"""Application exceptions. Messages are safe to show to end users (FR-18)."""


class BankError(Exception):
    """Base class for expected, user-presentable errors."""


class ValidationError(BankError):
    """Input failed validation."""


class AuthenticationError(BankError):
    """Login failed or is temporarily blocked."""


class PermissionDenied(BankError):
    """The current role may not perform this action."""


class NotFoundError(BankError):
    """A requested record does not exist."""


class DuplicateError(BankError):
    """A unique value already exists."""


class InsufficientFundsError(BankError):
    """The source account does not hold enough money."""


class AccountStateError(BankError):
    """The account (or customer) status does not allow the operation."""
