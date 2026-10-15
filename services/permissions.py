"""Role-based permission matrix (FR-01, NFR-04, business rule 7)."""
from exceptions import PermissionDenied

PERMISSIONS = {
    "admin": {"view", "reports", "export", "audit", "manage_staff", "backup", "reverse",
              "manage_kyc", "manage_loans", "approve_loans"},
    "teller": {"view", "reports", "export", "manage_customers", "manage_accounts", "transact",
               "manage_kyc", "manage_loans", "manage_interest"},
    "viewer": {"view", "reports", "export"},
}


def can(user, permission: str) -> bool:
    return bool(user) and getattr(user, "is_active", False) and permission in PERMISSIONS.get(user.role, ())


def require(user, permission: str) -> None:
    if not can(user, permission):
        raise PermissionDenied("Your role is not permitted to perform this action.")
